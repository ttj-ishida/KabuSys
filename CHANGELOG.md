CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

注: リリース日にはコードベースから推測した最新日付を使用しています。

[Unreleased]
------------

（現在のリポジトリ状態では新規変更なし）

[0.1.0] - 2026-03-31
-------------------

Added（追加）
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサー実装:
    - コメント行 / 空行を無視。
    - export KEY=val 形式対応。
    - シングル・ダブルクォート対応（バックスラッシュエスケープを考慮して閉じクォートを検索）。
    - クォートなし値中のインラインコメントは直前がスペース/タブの場合のみコメント扱い。
  - OS 環境変数保護機構（自動ロード時に既存の OS 環境変数を protected として上書き回避）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ化（必須環境変数未設定時は ValueError を返す）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - LOG_LEVEL のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - duckdb/sqlite のデフォルトパス設定。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメントスコアを算出。
    - チャンク単位（デフォルト最大20銘柄）でバッチ API 呼び出し。
    - スコアの ±1.0 クリッピング、レスポンスの厳密なバリデーション（results 配列・code・score）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）: 指数バックオフ実装。
    - テストのため _call_openai_api を patch 可能に設計。
    - タイムウィンドウ定義（JST 基準: 前日 15:00 ～ 当日 08:30 を UTC に変換して DB クエリに使用）。
    - DuckDB executemany の制約回避（空リスト送信を避けるガード）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日本225連動）について直近200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出用キーワード一覧を実装（日本・米国などのマクロ関連語）。
    - OpenAI 呼び出しに対する堅牢なリトライ/エラー処理。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - レジーム判定結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時に ROLLBACK を試行。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - ボラティリティ/流動性: 20 日 ATR / ATR 比率、20 日平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: raw_financials を用いた PER / ROE を計算する calc_value。
    - DuckDB を用いた SQL ベース実装。欠損やデータ不足時は None を返す設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算：calc_forward_returns（デフォルト horizons=[1,5,21]、horizons のバリデーションあり）。
    - IC（Information Coefficient）計算：calc_ic（スピアマンランク相関、必要レコード数のチェック）。
    - ランク関数：rank（同順位は平均ランク、丸めで ties の誤検出を防止）。
    - 統計サマリー：factor_summary（count/mean/std/min/max/median）。
  - research パッケージの公開 API を __all__ で整理。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar に基づく営業日判定および next/prev/get_trading_days/is_sq_day 関数を提供。
    - DB が未登録の日時は曜日ベース（週末は非営業日）でフォールバックする一貫したロジック。
    - calendar_update_job : J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）を行う設計を反映。
    - jquants_client 経由でのデータ取得 / 保存フローに準拠。
    - エラーは収集して呼び出し元へ返す（Fail-Fast ではなく呼び出し元で判断可能）。

- パッケージ初回エクスポート
  - kabusys.__init__ にて __version__ と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

Changed（変更）
- （初回公開のため該当なし）

Fixed（修正）
- （初回公開のため該当なし）

Security（セキュリティ）
- .env 自動ロード時に既存 OS 環境変数の上書きを防ぐため保護リストを利用（誤って機密情報を上書きしない設計）。
- OpenAI API キーの未設定時は明示的に ValueError を送出し、安全に処理を停止。

Notes（備考 / 設計上の注意）
- ルックアヘッドバイアス防止:
  - 各種処理（news スコアリング / レジーム判定 / ファクター計算等）は date 引数を明示的に受け取り、内部で datetime.today()/date.today() を参照しない方針。
  - DB クエリでは target_date 未満（排他）や LEAD/LAG を使った営業日ベースの参照等で将来データの漏洩を避ける。
- OpenAI 呼び出し:
  - JSON mode を利用して厳密な JSON レスポンスを期待する設計。レスポンスパース失敗時はフェイルセーフでスコアを無効化（0.0）または該当チャンクをスキップ。
  - テスト容易性のため _call_openai_api をモジュール内で分離して patch 可能にしている（unittest.mock.patch により差し替え可能）。
- DuckDB に関する互換性配慮:
  - executemany に空リストを渡すと失敗する既知の挙動（DuckDB 0.10）を回避するガード実装。
  - SQL 文や日付変換で DuckDB の戻り値型に対応するヘルパーを用意。

今後の改善候補（未実装）
- バリュー指標の拡張（PBR、配当利回りなど）。
- news_nlp / regime_detector のマルチモデル対応やプロンプト最適化の追加。
- ETL の詳細な品質チェックルールの拡張と自動アラート連携。

署名
----
この CHANGELOG は現在のコードベースの実装内容から推測して作成しています。実際のコミット履歴が存在する場合は差分や個別のコミットメッセージに合わせて調整してください。