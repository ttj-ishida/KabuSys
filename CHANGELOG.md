# CHANGELOG

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリースノートはコードベースから推測した実装・設計方針を基に作成しています。

すべてのバージョンはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買・データ基盤・リサーチ用の基本機能群を実装。

### Added
- パッケージ骨格
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の読み込み/管理を提供する Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート検出 (_find_project_root) により .git または pyproject.toml を基準に探索。
    - OS 環境変数 > .env.local > .env の優先度で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
  - .env パーサ実装（エクスポート構文対応、クォート・エスケープ・インラインコメント処理）。
  - 環境変数必須チェック用の _require と設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。
  - 各種デフォルト値（DUCKDB_PATH、SQLITE_PATH、KABU_API_BASE_URL 等）を設定。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション。

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント ai_score を算出して ai_scores に保存する機能（score_news）。
    - タイムウィンドウ計算（JST ベース）を提供する calc_news_window。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、レスポンス検証、スコアのクリップ（±1.0）。
    - レート制限・ネットワーク断・5xx に対するエクスポネンシャルバックオフ付きリトライ実装。
    - JSON レスポンスの頑健なパース（前後余分テキストのトリミング等）と安全なスキップ方針（API 失敗時も処理継続）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から MA200 乖離を計算、raw_news からマクロキーワードで抽出したタイトルを LLM に渡す。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ処理。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - LLM 呼び出しはニュースNLPと独立した実装でモジュール結合を避ける。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定ロジック: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない場合は曜日（土日）ベースでフォールバックする一貫した挙動。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装（J-Quants クライアントを経由して差分取得・冪等保存・バックフィル対応）。
    - 最大探索日数や健全性チェック等のセーフガードを追加。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（etl の実行結果、品質問題一覧、エラー一覧などを含む）。
    - 差分更新・バックフィル・品質チェック方針をコードに反映（設計に従った実装基盤）。
    - DuckDB に対する互換性注意（executemany の空リスト回避等）を考慮した実装。
  - ETL 再エクスポート（kabusys.data.etl）は ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR, 相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB SQL によって計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - SQL ウィンドウ関数を活用した効率的な実装。データ不足時の None 扱い。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク付け（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリのみで実装（pandas 不使用）。
    - ランクは同順位を平均ランクで処理し、丸めによる ties 判定の安定化を行う。

### Changed
- （初回リリースのため該当なし）

### Fixed
- エラー／例外処理の強化
  - OpenAI API 呼び出しの各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対する細かなハンドリングとリトライ方針を実装。
  - JSON パース失敗やレスポンス構造の崩れに対するフォールバック（警告ログ出力のうえスキップ）を追加。
  - DuckDB 書き込みでの部分失敗時に既存データを保護するため、書込み前に対象コードのみ削除してから挿入する手法を採用。
  - DB トランザクション中の例外発生時に ROLLBACK を試行し、ROLLBACK 自体が失敗した際は警告ログを出力する等の堅牢化。

### Security
- 環境変数の自動読み込みをプロセス外から無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。テスト時やセキュリティポリシーに合わせた挙動制御が可能。

### Notes / Known limitations
- calc_value: PBR・配当利回りは現バージョンでは未実装。
- AI 部分は OpenAI の JSON Mode（gpt-4o-mini）に依存し、モデル・API の変更があった場合は修正が必要。
- DuckDB のバージョン依存の挙動（リストバインドや executemany の空リストなど）に注意して実装しているが、将来の DuckDB バージョンでテストが必要。
- 日付関連処理は「ルックアヘッドバイアス防止」のために内部で datetime.today() / date.today() を参照しない設計（一部のバッチジョブなどで date.today() を使う箇所は限定的）。

---

この CHANGELOG はコードから推測した実装内容に基づいて作成しています。具体的な実装やリリース履歴はプロジェクトの実際のコミット履歴・リリースノートに合わせて更新してください。