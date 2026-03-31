Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

注意:
- 記載内容は提示されたコードベース（src/kabusys 以下）から推測してまとめています。
- バージョンはパッケージ内の __version__ ("0.1.0") に合わせています。
- 日付は本回答作成日（2026-03-31）を使用しています。必要に応じて公開日を変更してください。

---------------------------------------------------------------------
CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従って変更履歴を管理します。

フォーマット
- "Added", "Changed", "Fixed", "Removed", "Security" 等で分類します。
- 新しいリリースは上から順に記載します。

Unreleased
----------
（現在未リリースの変更はここに記載）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初回リリース（kabusys 0.1.0）。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - パッケージ公開対象のサブパッケージとして data, strategy, execution, monitoring を __all__ に列挙

- 設定・環境変数管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を取り込む自動ロード機能を実装
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - OS 環境変数の上書きを防ぐ保護機構（protected set）
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後も安定）
  - .env 行パーサーの実装: コメント、export プレフィックス、クォートとエスケープ対応を含む堅牢な解析
  - Settings クラスを提供（settings インスタンス経由で利用）
    - J-Quants、kabuステーション、Slack、データベースパス、監視閾値、実行環境（development/paper_trading/live）などのプロパティ
    - env / log_level の値検証とブロック（不正値で ValueError を送出）
    - Path 型プロパティは expanduser を行う

- AI 関連モジュール（src/kabusys/ai/**）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ（calc_news_window）
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数トリム、JSON mode の厳密バリデーション
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ、レスポンス検証で安全にスキップするフェイルセーフ設計
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（_call_openai_api を patch してモック）
    - ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジームを日次判定（bull/neutral/bear）
    - prices_daily と raw_news を参照、OpenAI（gpt-4o-mini）を利用（API キーは引数または環境変数 OPENAI_API_KEY）
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
    - API 例外に対する細やかなハンドリング（RateLimit/Connection/Timeout/5xx/その他）とリトライロジック
    - モジュール間の結合を避けるため news_nlp の内部関数を直接参照しない設計

- Research（ファクター計算・特徴量探索）（src/kabusys/research/**）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等の計算関数を実装
    - DuckDB を用いた SQL ベースの集計実装（prices_daily / raw_financials のみ参照）
    - 欠損やデータ不足時の挙動（None 戻し）を明確化
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを一括取得
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク処理（丸めで ties の誤差を抑制）
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算
  - 上記機能は pandas など外部ライブラリに依存せず標準ライブラリ + DuckDB で実装

- Data プラットフォーム関連（src/kabusys/data/**）
  - calendar_management.py
    - JPX カレンダーの管理と夜間更新ジョブ（calendar_update_job）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供
    - market_calendar が未取得のときは曜日ベースでフォールバック（週末を休業日扱い）
    - DB データ優先、未登録日は曜日判定で一貫性を担保（探索上限付き）
    - J-Quants クライアントを用いた差分取得・冪等保存との連携を想定
  - pipeline.py / etl.py
    - ETLResult データクラス（pipeline.ETLResult を etl モジュールで再エクスポート）
    - ETL パイプラインの責務、差分取得・保存・品質チェックの設計方針を反映
    - ETLResult に品質問題（QualityIssue）とエラー集約、to_dict メソッドを実装
    - DuckDB 上の最大日付取得やテーブル存在チェック等のユーティリティ

- その他
  - テスト容易性を意識した設計（OpenAI 呼び出しの差し替えポイント、環境変数ロード無効化フラグ等）
  - 多くの関数でルックアヘッドバイアスを防ぐ設計（date.today() を直接参照しない、target_date を明示するアプローチ）
  - ロギング（logger）を各モジュールで利用、処理経過・警告・例外時の情報出力を充実

Security
- OpenAI API キー（OPENAI_API_KEY）、J-Quants / Slack / kabu API の認証情報は環境変数で扱うことを前提
- .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能
- config モジュールは OS 環境変数を保護するため上書き制御（protected set）を導入

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Notes / Usage（抜粋）
- 設定読み取り:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path 等を参照
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- ETL 結果:
  - from kabusys.data import ETLResult

開発者向けメモ（設計判断の要点）
- ルックアヘッドバイアス防止のため全てのバッチ/解析系関数は target_date を明示的に受け取る
- OpenAI 呼び出し周りは 429 / ネットワーク / タイムアウト / 5xx をリトライし、それ以外は失敗したチャンクだけをスキップする（部分成功を許容）
- DuckDB の executemany の仕様差異（空リスト不可など）を考慮した実装
- モジュール間のプライベート関数共有を避ける設計（テスト時の差し替えは各モジュール内のラッパー関数を patch することを想定）

---------------------------------------------------------------------
今後の改善候補（コードからの推測）
- docs/ に API リファレンスや運用ドキュメント（環境変数一覧・.env.example・デプロイ手順）を追加する
- 単体テスト／統合テストの追加（OpenAI と外部 API をモックするテスト群）
- エラーモニタリング（Sentry 等）・再試行ポリシーの微調整
- パフォーマンス向上: 大量データ処理時のメモリ最適化や並列化検討

---------------------------------------------------------------------
以上。必要であれば日付の修正、より詳細なリリースノート（各関数の引数・戻り値の完全リストや例外仕様）を追加します。