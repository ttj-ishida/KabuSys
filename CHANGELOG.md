# CHANGELOG

このファイルは Keep a Changelog の形式に準拠します。  
現在の実装内容はコードベースから推測して記載しています。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリース: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / セキュリティ (Security) 等のカテゴリで記載

---

## [Unreleased]

- なし（初回公開相当の内容を以下に記載）

---

## [0.1.0] - 2026-04-04

初回公開（推定）。以下の主要機能と設計上の注意点を実装。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージを追加。エントリポイントで __version__ を "0.1.0" として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリ上で .git または pyproject.toml を探索する方式を採用（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの強化:
    - コメント行・空行・export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの扱い（クォートあり/なしでの違い）を考慮。
  - 必須設定取得ヘルパー `_require` と Settings クラスを提供。
    - OpenAI などの API キー、Kabu API パスワード、データベースパス、監視用ファイルパス、閾値、環境 (development/paper_trading/live) や LOG_LEVEL のバリデーションを実装。

- AI モジュール (`kabusys.ai`)
  - news_nlp モジュール:
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) に対して銘柄ごとのニュースセンチメントを JSON mode でバッチ評価。
    - チャンク処理 (最大 20 銘柄/チャンク)、トークン肥大化対策（記事数制限・文字数トリム）を実装。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリッピング。
    - テスト用に _call_openai_api を差し替え可能な設計。
    - ai_scores テーブルへの冪等的書き込み（該当コードのみ DELETE → INSERT）を実装。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（70%）と、news_nlp によるマクロセンチメント（30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - DuckDB からのデータ取得、OpenAI 呼び出し、失敗時フェイルセーフ（macro_sentiment=0.0）、冪等的な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しでのリトライ（最大回数・指数バックオフ）とエラー分類に基づく挙動を実装。
    - LLM 呼び出し部分は news_nlp と独立した実装でモジュール結合を避ける設計。

- Data モジュール (`kabusys.data`)
  - calendar_management:
    - JPX カレンダーの管理と夜間バッチ更新ジョブ (calendar_update_job) を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などの営業日判定ユーティリティを提供。
    - market_calendar テーブルが未取得の際は曜日ベース（土日休み）でのフォールバックを行う一貫した設計。
    - 最大探索日数やバックフィル・健全性チェック（未来日付異常検知）など安全策を実装。
    - J-Quants クライアント経由で差分取得 + 冪等保存を想定。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果、品質チェック結果、エラー情報を保持）。
    - ETL 設計における差分更新、バックフィル、品質チェック（quality モジュール）との連携を想定。
    - DuckDB 上の存在チェック・最終日取得ユーティリティを実装。

- Research モジュール (`kabusys.research`)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）およびバリュー（PER, ROE）ファクター計算機能を実装。
    - DuckDB を用いた SQL + Python の混合実装で、prices_daily / raw_financials だけを参照する安全設計。
    - 結果は date, code をキーとする dict のリスト形式で返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を提供。
    - 外部依存（pandas 等）は使用せず標準ライブラリで実装。
    - rank は同順位に対して平均ランクを返す実装。

### 変更 (Changed)

- 設計方針の明確化（コード内ドキュメント）
  - すべての AI/リサーチ処理で datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取ることでルックアヘッドバイアスを防止する方針を採用。
  - DB 書き込みは冪等操作（DELETE → INSERT、ON CONFLICT 想定）で部分失敗時の既存データ保護を重視。

### 修正 (Fixed)

- 初期実装リリースにつき特定のバグ修正履歴はなし（今後の実使用で追記予定）。

### セキュリティ (Security)

- 環境変数管理:
  - API キーやパスワードは環境変数経由で取得。必須値は _require で検証して未設定時に ValueError を投げる設計。
  - 自動 .env ロードを無効化するためのフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

### その他 / 実装上の注意

- 依存:
  - DuckDB（duckdb Python）、OpenAI Python SDK を前提とする実装。
- テスト容易性:
  - OpenAI 呼び出しを行う関数（_call_openai_api）はテスト時に差し替え可能に設計。
- ロギング:
  - 各モジュールで詳細なログ（info/warning/debug）を出力するようになっており、フェイルセーフ時はログで通知する設計。
- トランザクション管理:
  - DB 書き込み失敗時には ROLLBACK を試み、失敗があれば警告ログを出力する堅牢性を持つ。

---

今後のリリース候補（例）
- 0.2.0: 実際の ETL 実行スクリプト、監視・実行モジュール（execution, monitoring）の実装、Strategy モジュールの追加。
- 0.1.x: バグ修正、テストの拡充、OpenAI レスポンスのより堅牢な検証。

--- 

訳注:
- 本 CHANGELOG は提供されたコードソースからの推測に基づく初期リリース記録です。実際のリリース履歴や日付は開発方針に応じて調整してください。