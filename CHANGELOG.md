CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog の慣例に従っています。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
（なし）

0.1.0 - 2026-03-26
------------------
最初の公開リリース。日本株自動売買・データ基盤・リサーチのための基礎機能を実装しました。

Added
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - サブパッケージを公開: data, research, ai, execution, strategy, monitoring（__all__ にて宣言）。

- 設定・環境読み込み
  - 環境設定管理モジュール kabusys.config を追加。
    - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロードを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - .env パーサは export プレフィックスに対応、クォートやバックスラッシュエスケープ、インラインコメントルールなどを考慮した堅牢な実装。
    - OS 環境変数を protected として扱い、.env.local により既存変数の上書きが可能（優先度: OS > .env.local > .env）。
    - 必須設定取得時に未設定なら ValueError を投げる _require ヘルパーを提供。
    - 設定クラス Settings によるプロパティアクセスを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（OpenAI 統合）
  - kabusys.ai.news_nlp を追加:
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを gpt-4o-mini でバッチ評価。
    - 出力は JSON mode を期待し、レスポンスのバリデーション（構造・型・既知コード・数値性など）を実施。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対して指数バックオフを実装。
    - スコアは ±1.0 にクリップ、部分成功時の DB 書き換えは該当コードのみ DELETE→INSERT で置換（冪等）。
    - テスト容易性のため OpenAI 呼び出し関数をパッチ可能に実装（unittest.mock.patch で差し替え可能）。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）と記事トリミング（記事数・文字数上限）を実装。
    - バッチサイズ、最大記事数、最大文字数などの定数で挙動を制御。

  - kabusys.ai.regime_detector を追加:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ、リトライ／バックオフを実装。
    - レジームスコアはクリップして閾値でラベル付けし、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 外部設計上の注意点として、ルックアヘッドバイアスを避けるために datetime.today() を参照しない設計。

- データ基盤（Data）
  - kabusys.data.pipeline に ETL 基盤を追加:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェックの設計を反映。
    - DuckDB を用いた最大日付取得、テーブル存在チェック等のユーティリティを実装。

  - kabusys.data.calendar_management を追加:
    - JPX カレンダー管理（market_calendar）: is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB に登録があれば DB 値を優先、未登録日は土日フォールバック（曖昧なデータでも一貫した挙動）。
    - calendar_update_job により J-Quants から差分フェッチ・保存（バックフィルと健全性チェックを実装）。
    - 最大探索日数／バックフィル日数／先読み日数などの安全パラメータを設定し無限ループや誤動作を防止。

  - kabusys.data.etl を追加（pipeline.ETLResult の再エクスポート）。

- リサーチ機能（Research）
  - kabusys.research パッケージを追加。以下の機能を実装・公開:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
      - calc_value: raw_financials からの PER/ROE 計算（EPS が 0/欠損時は None）。
      - DuckDB のウィンドウ関数を活用し、営業日ベースでの計算を行う。
    - feature_exploration:
      - calc_forward_returns: target_date から任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコード <3 の場合は None）。
      - factor_summary: count/mean/std/min/max/median の統計量出力。
      - rank: 同順位は平均ランクで処理（丸め対策あり）。
    - kabusys.research は kabusys.data.stats の zscore_normalize を再利用可能にインポート。

- DuckDB を中心とした DB モデル
  - 多くのモジュールが DuckDB 接続を受け取り prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime などのテーブルを参照・更新する設計。

Security
- 環境変数や API キーは必須チェックを行い、未設定の場合は明確なエラーメッセージ（ValueError）を出力。
- .env ファイル読み込み時に OS 環境変数を保護する仕組み（protected set）を実装。

Behavioral / Design notes
- ルックアヘッドバイアス排除: ランタイムに date.today() を参照しない設計方針を主要な分析・スコアリング関数で採用。
- フェイルセーフ設計: AI API の障害時は例外を即時伝播させず、安全側の既定値（例: macro_sentiment=0.0）で継続する箇所がある（運用上の可用性重視）。
- テストフレンドリー: OpenAI 呼び出しポイントはモジュール内の private 関数を patch して差し替えやすい作り。
- DB 書き込みは冪等性を考慮（DELETE→INSERT、または ON CONFLICT による上書き）しているため、再実行による重複問題を避ける。

Breaking Changes
- 本リリースが最初の公開バージョンのため、破壊的変更はありません。

Migration / Usage Notes
- 必要な環境変数:
  - OPENAI_API_KEY（news_nlp / regime_detector 利用時）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 利用）
  - KABU_API_PASSWORD（kabu ステーション API 利用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知連携）
  - KABUSYS_ENV（development|paper_trading|live）
  - LOG_LEVEL（DEBUG|INFO|...）
  - DUCKDB_PATH / SQLITE_PATH（DB ファイルパス）
- 自動 .env 読み込みはデフォルトで有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB をバックエンドに使うため、対象プロジェクトでは必要テーブル（prices_daily 等）を事前に作成しておく必要があります。
- OpenAI 呼び出しは gpt-4o-mini（モデル名）を利用する想定。API レスポンスは JSON モードを期待します。

Notes / Known limitations
- 現時点で PBR・配当利回り等の一部バリューファクターは未実装（calc_value では per と roe のみ）。
- news_nlp のレスポンスバリデーションで LLM の出力が期待フォーマットにならない場合は該当チャンクをスキップするため、一部銘柄でスコアが取得できない可能性があります（部分成功は許容して他データを保護する設計）。
- DuckDB の executemany に対して空リストを与えないように注意した実装（互換性対応）。

Acknowledgements
- J-Quants、kabu ステーション、OpenAI などの外部サービスとの連携を想定した実装が含まれます。API の仕様変更があった場合、該当クライアントラッパー（kabusys.data.jquants_client 等）の更新が必要です。

--- 
今後のリリースでは、以下を予定しています（例）:
- 追加ファクターの実装（PBR、配当利回りなど）
- モデル学習/バックテストモジュールの追加
- 発注実行部分（execution）と戦略（strategy）の統合テスト補強
- jquants_client / kabu API クライアントの具象実装とエラーハンドリング強化

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートとして用いる場合は、実際のコミット履歴やリリース差分を元に適宜調整してください。