# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
semantic versioning を使用します。

現在日付: 2026-04-03

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システムの基盤機能を実装しています。主な追加点・設計方針・フェイルセーフは以下の通りです。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない実装）。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート外ではスペース前の # をコメントと判定）
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須キー取得関数 _require と Settings クラスを提供（J-Quants / kabu / LINE / DB / 監視 / システム設定用プロパティ）
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL の許可値チェック）と利便性メソッド（is_live / is_paper / is_dev）

- AI（自然言語処理）モジュール（src/kabusys/ai/）
  - ニュースセンチメント分析（news_nlp.py）
    - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価を実装
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）と DuckDB からの銘柄別記事集約
    - 1銘柄当たりの記事数・文字数上限、バッチ（最大20銘柄）での API 呼び出し
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列の検査、コード／スコア検証）
    - ai_scores テーブルへ冪等的に書き込む処理（部分失敗時に既存データを守る設計）
    - テスト容易性: _call_openai_api の差し替えを想定
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）判定
    - calc_news_window と連携して lookahead を防止する設計
    - OpenAI 呼び出し・リトライロジック（3回）とフェイルセーフ（API 失敗時は macro_sentiment=0.0 で継続）
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT, ロールバック処理あり）
    - モジュール間の結合を避けるために OpenAI 呼び出し関数を独立実装

- データ基盤関連（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー取得用の夜間バッチジョブ calendar_update_job 実装（J-Quants クライアントと連携）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供
    - market_calendar 未取得時は曜日ベース（平日=営業日）でフォールバックする堅牢設計
    - 最大探索日数制限や健全性チェック（未来日付の閾値）を実装
  - ETL パイプライン（pipeline.py / etl.py / __init__.py）
    - ETLResult データクラス（実行結果、品質問題、エラーの集約）
    - 差分取得、バックフィル、IDempotent 保存、品質チェックの枠組みを用意
    - jquants_client / quality モジュールと連携する設計を想定
    - etl モジュールは ETLResult を公開（再エクスポート）

- 研究（research）モジュール（src/kabusys/research/）
  - factor_research.py
    - Momentum（1m/3m/6m リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）等のファクター計算を実装
    - DuckDB に対する SQL ウィンドウ関数を多用し、営業日ベースの窓や欠損処理を考慮
    - 結果を (date, code) をキーとした dict のリストで返す
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算（Spearman ランク相関） calc_ic
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - ファクターの統計サマリー factor_summary（count/mean/std/min/max/median）
  - research パッケージ初期エクスポートヘルパを提供（主要関数を __all__ で公開）

### 変更（設計・実装上の注記）
- ルックアヘッドバイアス対策
  - news_nlp、regime_detector、research の関数群は内部で datetime.today()/date.today() を参照せず、外部から target_date を明示的に渡す設計。DB クエリも target_date 未満・未満等でルックアヘッドを防止。
- DB 書き込みは冪等性を重視
  - market_regime / ai_scores 等への書き込みは一旦 DELETE して INSERT（トランザクション管理）することで上書きを安全に行う。
  - DuckDB の executemany 空リスト問題に配慮したチェックを実装。
- API 呼び出しの堅牢性
  - OpenAI 呼び出し（news_nlp/regime_detector）での 429/接続断/タイムアウト/5xx に対するリトライ実装（指数バックオフ）
  - レスポンスパース失敗や非致命的エラーはログを出してフォールバック（例: スコア 0.0 やスキップ）するフェイルセーフ方針。

### 修正（バグフィックス相当）
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ処理、export プレフィックス、インラインコメント判定の修正により実務での .env 取り込み精度を向上。
- JSON モードの余剰テキスト対策
  - OpenAI の JSON mode でも前後に余計なテキストが混ざる場合を想定して最外側の {} を抽出して復元するロジックを追加（news_nlp のバリデーション）。

### セキュリティ・運用上の注意
- OpenAI API キーの取り扱い
  - news_nlp と regime_detector は api_key 引数または環境変数 OPENAI_API_KEY を必須とする。未設定時は ValueError を送出。
- 環境変数保護
  - .env ロード時、OS 環境変数は protected として上書きされない（env ロードの override ロジックにより制御可能）。
- 実行監視設定
  - pid ファイル/kill フラグ/リソース閾値（CPU/MEM/DISK）等の設定を環境変数経由で管理可能。

### 既知の制限・今後の課題
- 一部ファクター（PBR・配当利回り）や発注・実行ロジックは未実装（このリリースはデータ・研究・NLP 基盤が中心）。
- DuckDB 互換性
  - executemany の空リスト不可やバインドリストの挙動に依存する部分があるため、DuckDB のバージョンによる差異に注意が必要。
- テスト
  - OpenAI 呼び出しはモックで差し替え可能だが、外部 API を使う処理は統合テストでの環境構築が必要。

---

（注）この CHANGELOG はソースコードから実装意図や注釈を抽出して推測に基づき作成しています。実際のリリースノートとして利用する場合は、開発履歴・コミットログと照合のうえ必要に応じて調整してください。