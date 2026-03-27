# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（今後の変更をここに記載します）

## [0.1.0] - 2026-03-27
初回公開リリース。本リポジトリは日本株の自動売買／データプラットフォームを想定したライブラリ群をまとめています。以下はコードベースから推測される主要な追加機能・設計上の注意点です。

### 追加
- 基本パッケージ
  - kabusys パッケージの公開エントリポイントを用意（__version__ = 0.1.0）。主要サブパッケージとして data / research / ai / ... をエクスポート。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検知: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 高度な .env パーサ実装（クォート内のエスケープ、export プレフィックス、インラインコメント取り扱いをサポート）。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や DB パス、環境（development/paper_trading/live）・ログレベル検証ロジックを公開。
  - 環境変数必須チェック用の _require ユーティリティ。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）および夜間バッチ更新 job（calendar_update_job）。DB 未取得時の曜日ベースフォールバック、健全性チェック、バックフィル対応を実装。
  - pipeline / etl: ETL パイプライン基盤。差分取得・保存・品質チェックを想定した ETLResult データクラス、テーブル存在チェックや最大日付取得ユーティリティ等を提供。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI（kabusys.ai）
  - news_nlp: ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ書き込む score_news 関数。バッチ処理、トークン肥大化に対するトリム、JSON Mode を想定したレスポンスバリデーション、429/ネットワーク/5xx に対する指数バックオフリトライなどを実装。
  - regime_detector: ETF（コード 1321）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする score_regime 関数。LLM 呼び出し失敗時のフェイルセーフやルックアヘッドバイアス対策を実装。
  - AI モジュールはいずれも OpenAI クライアント呼び出し箇所をテスト容易に差し替え可能（内部 _call_openai_api を patch 可能）。

- リサーチ（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB SQL とウィンドウ関数を活用。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
  - research パッケージは主要関数を __all__ で再エクスポート。

- DuckDB 統合
  - 多数のモジュールで duckdb.DuckDBPyConnection を受け取り、prices_daily/raw_news/raw_financials/ai_scores/market_regime/market_calendar 等のテーブルを参照・更新する実装を採用。
  - DB 書き込みは冪等性（DELETE→INSERT または ON CONFLICT）やトランザクション（BEGIN/COMMIT/ROLLBACK）を意識して実装。

### 変更（設計上の追加説明）
- ルックアヘッドバイアス対策を徹底
  - datetime.today() / date.today() を内部ロジック（AI スコア算出・ファクター計算等）で直接参照しない設計。target_date を明示的に受け取る API として実装。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants 等）呼び出しが失敗した場合に、処理を停止させず安全側の既定値（例: macro_sentiment=0.0、スコア未取得扱い）で続行する箇所が多数存在。
- .env 読み込みの上書きポリシー
  - .env と .env.local の読み込み順を定義（OS 環境 > .env.local > .env）。既存 OS 環境は protected として上書きを防ぐ。

### 修正（実装上の堅牢化）
- OpenAI レスポンスの厳格なバリデーションとパース保護（JSON パース失敗時のフォールバックロジックや余分な前後テキストの復元試行）。
- API エラー処理で status_code の有無に対応（SDK の将来変更を考慮して getattr を使用）。
- DuckDB の executemany に関する互換性（空リストを渡さない）を考慮した実装。
- 各種ログ出力の追加により運用時の診断性を向上。

### 既知の制限 / 注意点
- OpenAI API キーは明示的に引数で注入するか環境変数 OPENAI_API_KEY を設定する必要がある（未設定時は ValueError を送出）。
- 一部処理は外部モジュール（jquants_client, quality 等）に依存しており、それらの実装が必要。
- DuckDB テーブルスキーマや外部 API のレスポンス仕様に依存するため、実運用にはスキーマ整備と API 資格情報の設定が必要。
- セキュリティ関連（機密情報の保護、鍵の管理）は設定管理側（環境変数、CI/CD）で適切に取り扱うこと。

### セキュリティ
- 本バージョンで特定のセキュリティ脆弱性はコードから明示されていないが、外部 API キー・トークン管理およびログ出力に含まれる可能性のある機密情報に注意してください。

---

配布・運用前に README やドキュメントで以下を明確化することを推奨します:
- 必須環境変数一覧と .env.example
- 必要な DuckDB テーブルスキーマ
- jquants_client / quality 等の依存実装方法
- OpenAI トークンの取り扱いポリシー

（以上、コードベースの内容から推測して記載しました。実際の変更履歴は git のコミット履歴等を基に作成してください。）