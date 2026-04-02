# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買・データ基盤のコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__、__version__ = "0.1.0"）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理
  - Settings クラスを実装し、環境変数経由で設定を取得可能に（J-Quants, kabuステーション, Slack, DB パス, 監視閾値など）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env パーサを実装し、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - OS 環境変数を保護する protected キーセット機構を導入（.env.local などによる上書き制御）。
  - 自動読み込みを無効化する環境変数フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

- AI（自然言語処理）
  - ニュース NLP モジュール（kabusys.ai.news_nlp）を追加：
    - raw_news / news_symbols を集約して、OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄ごとのセンチメントスコアリングを実装。
    - チャンク・バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数上限・文字数トリムをサポート。
    - レスポンス検証・スコアの ±1.0 クリップ、部分的書換（DELETE → INSERT）により部分失敗時に既存データを保護。
    - API 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフォールバック動作。
    - タイムウィンドウは JST 基準で厳格に定義し、ルックアヘッドバイアスを防止（日時の直接参照を避ける設計）。

  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）を追加：
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュースのキーワードフィルタリング、OpenAI 呼び出し、スコア合成、冪等的な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時は macro_sentiment を 0.0 として継続するフェイルセーフを備える。

- データプラットフォーム
  - ETL パイプライン基盤（kabusys.data.pipeline）を追加：
    - 差分取得 → 保存（jquants_client 経由で idempotent 保存）→ 品質チェック のワークフローを想定した構造。
    - ETLResult dataclass を実装し、実行サマリ（取得数・保存数・品質問題・エラーなど）を表現。
  - ETL の公開インターフェースを etl モジュールで再エクスポート（ETLResult）。
  - マーケットカレンダー管理モジュール（kabusys.data.calendar_management）を追加：
    - market_calendar テーブルを基にした営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - J-Quants API からの夜間バッチ更新ジョブ（calendar_update_job）を実装。バックフィルや健全性チェックを含む。

- リサーチ機能
  - research パッケージを追加し、以下の機能を提供：
    - ファクター計算（kabusys.research.factor_research）: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金等）、バリュー（PER/ROE）を DuckDB SQL ベースで計算。
    - 特徴量探索（kabusys.research.feature_exploration）: 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - kabusys.data.stats の zscore_normalize を再エクスポートするユーティリティ。

### 変更 (Changed)
- なし（初回リリースのため、既存変更はありません）。

### 修正 (Fixed)
- OpenAI レスポンスの取り扱い強化：
  - JSON mode であっても前後に余計なテキストが混入するケースに対して最外の `{...}` を抽出してパースする耐性を追加。
  - レスポンス構造（results / code / score）のバリデーションを実装し、不正なレスポンスは該当チャンク・銘柄のみスキップする設計に。
- API エラー時の挙動安定化：
  - リトライ対象エラー（RateLimitError, APIConnectionError, APITimeoutError, 5xx）と非リトライ対象を明確化し、ログを出力してフォールバック（0.0 やスキップ）するようにした。
- DuckDB への書き込み互換性対応：
  - DuckDB 0.10 の executemany が空リストを受け付けない制約を回避するため、空パラメータのケースを事前チェックして処理をスキップするロジックを追加。
- 時系列バイアス対策：
  - すべての AI / スコア計算（score_news, score_regime 等）は内部で datetime.today() / date.today() を直接参照せず、外部から渡される target_date を基準に処理する設計によりルックアヘッドバイアスを回避。

### セキュリティ (Security)
- OpenAI API キーが未設定の場合は明示的な例外を発生させユーザーに通知（api_key 引数または OPENAI_API_KEY 環境変数の設定を要求）。
- 環境変数の自動ロードでは OS 環境変数を保護（.env ファイルによる誤上書きを防止）。

### 注意事項 / 既知の制約 (Notes / Known issues)
- OpenAI 呼び出しは外部 API に依存するため、API キーの管理・レート制限・コストに注意が必要です。ローカルテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数や unittest.mock による _call_openai_api の差し替えを推奨します。
- DuckDB のバージョン差異により一部 SQL バインドの挙動が異なる可能性があるため、DuckDB の互換性テストを実施してください。
- 現在の ai_scores / market_regime 等のスキーマは本コードに依存しており、運用前に DB スキーマ定義を確認してください。
- strategy / execution / monitoring の具体的な発注ロジックや監視エージェントは本リリースでは限定的（もしくは未実装）であり、本 CHANGELOG はライブラリ提供機能に重点を置いています。

---

今後のリリースでは、戦略実装（発注・ポジション管理）、より詳細な監視・アラート機能、パフォーマンス最適化、テストカバレッジ拡充などを予定しています。