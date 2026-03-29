# Changelog

すべての注目に値する変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。セマンティックバージョニングを採用しています。

- 最新: Unreleased
- リリース日付の表記は YYYY-MM-DD

---

## [Unreleased]

追加予定 / 推定改善点（コード内コメントや設計方針から推測）
- テスト強化
  - OpenAI 呼び出しや環境変数ロードのユニットテスト（`unittest.mock.patch` を使った API モックの追加）。
  - DuckDB に対するエッジケース（executemany の空リスト等）を対象とした回帰テスト。
- ドキュメント・運用改善
  - .env.example の整備とデプロイ手順の明文化。
  - ETL／カレンダー更新ジョブの監視やアラート設定の追加。
- モデル・スコアリング改良
  - news_nlp / regime_detector のプロンプト改善やスコアリングの追加検証ロジック。
  - ファクター群（Value の PBR や配当利回りなど）の追加実装。
- 依存関係・互換性
  - DuckDB のバージョン固有の挙動に対する互換性テストの拡充。
  - OpenAI SDK のバージョン差異に対する対応テスト（status_code 等の扱いは既に考慮済み）。

---

## [0.1.0] - 2026-03-29

初回公開（推定）。日本株自動売買プラットフォームのコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージルート `kabusys` を追加。バージョン情報 `__version__ = "0.1.0"` を設定。
  - モジュール公開 API の初期整備（`__all__` に data / strategy / execution / monitoring を想定）。

- 設定管理（kabusys.config）
  - .env ファイル・環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - 複雑な .env パースロジックを実装（export プレフィックス対応、クォート内のエスケープ、インラインコメントの扱い等）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等のプロパティを提供。
  - 環境値検証を導入（`KABUSYS_ENV`，`LOG_LEVEL` の許容値チェック）、必須変数未設定時は明示的なエラーを投げる `_require` を実装。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュール
    - raw_news + news_symbols を元にニュース記事を銘柄毎に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出、`ai_scores` テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換ロジックを提供（calc_news_window）。
    - バッチサイズ、文字数制限、再試行（429/タイムアウト/5xx に対する指数バックオフ）を実装。
    - OpenAI レスポンスの堅牢なバリデーションと ±1.0 でのクリップ処理を実装。
    - 部分失敗時に既存スコアを保護するため、影響範囲を絞って（対象コードのみ）DELETE → INSERT を実行。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LL M センチメント（重み 30%）を合成して、日次で市場レジーム（bull / neutral / bear）を判定し、`market_regime` テーブルへ冪等的に保存。
    - MA 計算はルックアヘッド防止（target_date 未満のみ使用）。
    - LLM 呼び出しは独立実装（モジュール分離）し、API エラー時のフォールバック（macro_sentiment=0.0）を用意。
    - 冪等書き込みのためトランザクション（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK を実装。

- 研究用ファクター群（kabusys.research）
  - factor_research モジュール
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離率の算出（calc_momentum）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の算出（calc_volatility）。
    - Value: PER、ROE の算出（raw_financials を参照する calc_value）。PBR/配当利回りは未実装として注記あり。
    - DuckDB 上で SQL と Python を組み合わせて効率的に計算。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）を汎用ホライズンで実装（デフォルト [1,5,21]）。
    - IC（Information Coefficient, スピアマン ρ）計算機能（calc_ic）。
    - ランキング変換（rank）とファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない実装方針（pandas 等に依存しない）。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）用ユーティリティと夜間バッチ更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末休業）を提供。
    - 最大探索範囲や健全性チェック、バックフィル戦略を実装。
  - pipeline / etl
    - ETLResult データクラスを実装し、ETL の取得数・保存数、品質チェック結果、エラー一覧を格納・変換する API を提供。
    - ETL の差分更新・バックフィル・品質チェック設計を想定した基盤コード（pipeline の実装方針コメント含む）。
  - etl モジュール
    - pipeline.ETLResult の再エクスポートを提供（外部公開インターフェース）。

- 通常運用上の堅牢性改善
  - DuckDB でのトランザクション運用 / ROLLBACK 失敗時の警告ログ等の例外処理を追加。
  - OpenAI API 呼び出し時の細かな例外（RateLimit/Timeout/Connection/APIError）を考慮したリトライ実装。
  - レスポンスパース失敗時には例外を投げずフォールバックするフェイルセーフ戦略を採用（継続的なバッチ処理を重視）。

### Changed
- （初版のためなし）設計上の意図や注記を実装内ドキュメントとして多数追加。  
  例: ルックアヘッドバイアス防止・部分失敗時の DB 保護・外部 API 呼び出しの独立化等。

### Fixed
- 実運用を想定した多数の防御コードを実装
  - DuckDB executemany の空リスト問題への対応（空時は呼ばない）。
  - OpenAI レスポンスの JSON 抽出失敗に対する復元処理（前後に余計なテキストが混ざるケースのハンドリング）。
  - API エラーのステータスコード存在性を安全に扱う（getattr を使用）。

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- 環境変数による API キー管理を前提。必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）は Settings 経由で厳密に要求する。
- .env の自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストや CI での誤読込みリスクを低減。

---

注記:
- 本 CHANGELOG はソースコード内のドキュメント、関数の振る舞い、ログメッセージ、設計方針コメント等から推測して作成しています。実際のリリース履歴や追加機能はリポジトリのコミット履歴やリリースノートをご確認ください。