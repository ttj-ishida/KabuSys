CHANGELOG
=========
（本ファイルは Keep a Changelog のフォーマットに準拠しています。主要な変更点を日本語でまとめています。）

Unreleased
----------
- 今後の予定（例）
  - ユニットテスト・統合テストの強化（OpenAI / 外部APIのモック整備）
  - CI / 自動デプロイ設定の追加
  - kabu ステーションとの発注実装（execution モジュールの拡充）
  - jquants_client の実装・依存解消に向けたリファクタリング

[0.1.0] - 2026-03-28
--------------------
初期リリース — 日本株自動売買システムの基本コンポーネントを提供。

Added
- パッケージ構成
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0）。
  - モジュール群: data, research, ai, config, （将来的に strategy, execution, monitoring 想定）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスでアプリ設定をラップ（必須環境変数は _require で検証）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須設定として取得。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証（development / paper_trading / live、DEBUG/INFO/...）。
    - DB パスのデフォルト (DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db)。

- データ基盤（kabusys.data）
  - ETL パイプラインの公開インターフェース（ETLResult の定義）。
  - pipeline モジュール:
    - 差分取得・バックフィル・品質チェックの考え方に基づく ETLResult データクラスを実装。
    - DuckDB 上での最終日取得ユーティリティ等を提供。
  - calendar_management:
    - JPX（マーケット）カレンダーの管理・夜間更新処理（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar が未取得の際は曜日ベース（土日非営業）でフォールバックする堅牢な設計。
    - バックフィル、先読み、健全性チェック（最大探索日数、将来日付の異常検出）をサポート。

- AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄センチメントを評価。
    - JSON Mode を使った厳密なレスポンス期待、レスポンスのバリデーション（results 配列、code/score）を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄当たりの最大記事数・文字数制限（トークン肥大対策）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - DuckDB の executemany における空リスト問題を回避する処理（空時は実行しない）。
    - calc_news_window: JST 基準のニュース収集ウィンドウ計算ユーティリティを提供（ルックアヘッドバイアスを避ける設計）。
  - regime_detector:
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは JSON レスポンスパースを期待、リトライロジックを実装。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - レジームはスコアを [-1,1] にクリップし閾値でラベル付け。結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 設計方針として datetime.today() などの直接参照を避け、target_date に依存することでルックアヘッドバイアスを防止。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB の SQL と組み合わせて計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い等、実運用での欠損処理を考慮。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（スピアマンのランク相関）、rank、factor_summary 等の統計・探索ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリで完結する実装。

- DuckDB を一貫して利用
  - 各モジュールは DuckDB 接続を受け取り prices_daily/raw_news/raw_financials/market_calendar 等のテーブルを参照・更新する設計。

Changed
- （初期リリースのため該当なし）

Fixed
- DuckDB executemany の空リストバインド制約に対する回避処理を導入（ETL、ai の書き込み処理）。

Security
- 秘密情報は環境変数経由で取り扱い（OpenAI API キー、J-Quants トークン、kabu API パスワード、Slack トークン等は必須設定として取得）。
- .env 自動読み込みを明示的に無効化できる仕組みを用意（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Implementation Details
- OpenAI 呼び出し:
  - gpt-4o-mini をデフォルトモデルに指定。
  - JSON mode を用い厳密な JSON を期待するが、万が一前後にノイズが混入した場合に {} を抽出して復元を試みる処理あり。
  - リトライポリシーは 429 / 接続エラー / タイムアウト / 5xx を対象に指数バックオフ（最大リトライ回数は各モジュールで定義）。
  - テスト容易性のため _call_openai_api をパッチで差し替え可能。
- ルックアヘッドバイアス対策:
  - 全体的に date/datetime の扱いは target_date ベースで明示的に設計。datetime.today()/date.today() の直接参照は最小化（calendar_update_job は実運用で date.today() を使用）。
- DB 書き込み:
  - idempotent な書き込み（DELETE → INSERT や ON CONFLICT 相当）を基本とし、部分失敗時に既存データを保護する方針。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を担保。
- ログ出力:
  - 各種失敗時に WARNING/INFO/DEBUG ログを出力しフェイルセーフで継続する設計（LLM 失敗時はスコアを 0.0 とする等）。

Breaking Changes
- 該当なし（初期リリース）。

Acknowledgements
- DuckDB を中心に据えた設計。
- OpenAI API（gpt-4o-mini）を利用する設計思想（JSON Mode、厳密なレスポンス検証）。

Footer
------
- この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時はリリース担当者のレビュー・追加情報（実装外の運用手順、マイグレーション手順、依存ライブラリのバージョン等）を反映してください。