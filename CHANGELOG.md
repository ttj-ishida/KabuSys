# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。これは Keep a Changelog の慣習に従っています。  
フォーマット: https://keepachangelog.com/ja/

注: 記載内容は提供されたコードベースの実装から推測した変更点・リリース内容です。

## [Unreleased]
- 今後の変更予定・進行中の作業をここに記載します。

---

## [0.1.0] - 2026-03-28
初回公開リリース。日本株の自動売買・データ基盤・リサーチ・AI支援のためのコアライブラリを提供します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージ群を公開: data, research, ai, monitoring（__all__ 指定）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - export 形式やシングル/ダブルクォート、エスケープ、行内コメント等に対応した .env パーサを実装。
  - 読み込み優先順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラスを提供し、必須環境変数取得のラッパー（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）と検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）等のデフォルトを定義。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX 市場カレンダーの管理・夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベースのフォールバックを採用。探索の最大日数上限を設定して無限ループを防止。
    - J-Quants クライアント経由での差分取得と idempotent な保存（save_* 側に委譲）。
  - pipeline / ETL:
    - ETLResult データクラスを追加（取得件数、保存件数、品質チェック結果、エラー一覧を保持）。
    - ETL 実行に関するユーティリティ（最終取得日の判定、テーブル存在チェック等）を実装。
    - backfill による後出し修正吸収や品質チェックとの連携を想定。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント評価を実装（score_news）。
    - バッチ処理（最大 20 銘柄 / コール）、1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、JSON Mode レスポンスの検証とクリッピング（±1.0）。
    - レート制限・ネットワーク障害・5xx に対する指数バックオフによる再試行、および失敗時のフォールバック（スキップ・ログ出力）。
    - DuckDB の executemany の制約を考慮し、空リスト回避ロジックを実装。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で市場レジーム（bull / neutral / bear）を判定（score_regime）。
    - MA とマクロを重み (70% / 30%) で合成、閾値に基づくラベル付け。結果を market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し、再試行・フォールバック（API 失敗時は macro_sentiment=0）を実装。
  - テスト容易性を考慮し、OpenAI 呼び出し部分はモジュール内で抽象化（_call_openai_api）しモック可能。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）、PER・ROE の算出関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL ベースでのスキャン範囲設計（バッファ日数）・データ不足時の None 処理。
  - feature_exploration:
    - 将来リターンの計算（calc_forward_returns、任意ホライズン対応、入力検証）。
    - IC（スピアマンのランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - kabusys.data.stats からの zscore_normalize を再公開するための __init__ 統合。

### Changed
- 設計方針明示（初版実装だが以下を重視）
  - ルックアヘッドバイアス回避: 各種処理で datetime.today()/date.today() を直接参照せず、target_date に依存する設計。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定、部分失敗時の既存データ保護）。
  - DuckDB の互換性・制約（executemany の空リスト禁止等）を考慮した実装。

### Fixed
- 安全性・堅牢性向上
  - .env 読み込み時のファイルアクセス例外を警告に置換し処理継続。
  - OpenAI レスポンスパースや API エラー時は例外を上位に投げずフェイルセーフ（ログ記録してスコアを無効化またはスキップ）することでバッチ処理の継続性を確保。
  - DuckDB 日付値の変換ユーティリティを追加し型不一致リスクを軽減。

### Security
- なし（既知のセキュリティ関連変更はこのリリースには含まれません）。  
  - 注意: 実行には外部機密情報（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN など）が必要です。環境変数の管理・配布には注意してください。

### Notes / Requirements
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - JQUANTS_REFRESH_TOKEN（データ取得）
  - KABU_API_PASSWORD（発注連携 / kabu API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
- DB: DuckDB を主要な内部ストレージとして使用。SQLite は監視用に想定。
- OpenAI モデル: gpt-4o-mini を想定（JSON Mode を活用）。
- テスト: OpenAI 呼び出し部やタイムウェイト等はモック可能にしてユニットテストの容易性を確保。

---

メンテナー向け補足:
- 将来的には以下が次の改善候補です（例: Unreleased に移行予定）
  - ai モジュールのローカル（オンプレ）フェイルバックや代替モデルのサポート。
  - ETL のより詳細な品質チェック結果収集と自動リカバリポリシー。
  - publish/subscribe によるリアルタイム処理パイプライン、並列化の最適化。
  - エンドツーエンドの統合テスト・CI における DuckDB スキーマ初期化ユーティリティの追加。

---