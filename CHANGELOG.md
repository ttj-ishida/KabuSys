# Changelog

すべての重要な変更は Keep a Changelog の形式で記録します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export 宣言、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスで主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使って銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - ニュースウィンドウ（JST基準）:
    - 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive に変換して比較）
  - バッチ処理: 1APIコール当たり最大 20 銘柄（_BATCH_SIZE）。
  - 1銘柄あたりの記事上限: 最新 10 件、文字数上限 3000 文字でトリム。
  - OpenAI 呼び出し: JSON mode（response_format={"type": "json_object"}）を使用、レスポンスをバリデーションしてスコアを ±1.0 にクリップ。
  - リトライ/フェイルセーフ:
    - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ（最大回数・基底待機秒数は定数化）。
    - API 失敗やパース失敗は該当チャンクをスキップし、処理継続（例外を破棄してフェイルセーフ）。
  - DuckDB 書き込みは冪等性を考慮（DELETE → INSERT、executemany で個別 DELETE、空リストの扱いに配慮）。
  - テスト容易性:
    - OpenAI 呼び出しは _call_openai_api を介しており、テストで差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で regime_label（bull/neutral/bear）を算出し market_regime テーブルへ書き込み。
  - マクロニュース抽出: raw_news から定義済みのマクロキーワードでフィルタ（最大 20 件）。
  - OpenAI（gpt-4o-mini）を使用し JSON レスポンスを期待、API エラー等は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
  - スコア合成としきい値:
    - 合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - bull/bear 判定に閾値 0.2 を採用
  - DB 書き込みはトランザクションで冪等（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試みる。

- データ関連（kabusys.data）
  - ETL の公開インターフェース: ETLResult を再エクスポート (kabusys.data.etl)。
  - pipeline モジュール:
    - 差分取得、保存（jquants_client を通じて idempotent に保存）、品質チェック（quality モジュールとの連携）を想定した ETLResult データクラスを実装。
    - backfill（デフォルト 3 日）や最小データ日付等の定数管理。
    - DuckDB の最大日付取得やテーブル存在チェック等のユーティリティ。
  - market_calendar 管理（calendar_management）:
    - JPX カレンダーを J-Quants から差分取得して market_calendar テーブルへ保存する夜間バッチ job（calendar_update_job）。
    - 営業日判定・前後営業日取得・期間内営業日リスト取得・SQ日判定のユーティリティを提供。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業日）。DB 登録ありの場合は DB 値優先、未登録日は曜日フォールバックで一貫性を保つ。
    - バックフィル日数や先読み日数、健全性チェック（将来日付の異常検出）を実装。

- 研究（research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）などのファクター計算関数を提供。
    - DuckDB SQL を利用し prices_daily / raw_financials のみ参照。結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、ファクター統計サマリー（factor_summary）を実装。
    - Pandas 等の外部依存を持たず、標準ライブラリ + DuckDB で実装。
  - research パッケージ __all__ を整備して主要関数を外部公開。

- 汎用設計方針と実装上の配慮
  - ルックアヘッドバイアス防止: 各種モジュールで datetime.today() / date.today() を直接参照しない（target_date を引数として扱う）。
  - DuckDB を主要な分析 DB として利用。
  - OpenAI 連携部分は例外的な API エラーに対するリトライとフォールバック（安全第一）。
  - テストしやすさのため、API キー注入や内部 API 呼び出しの差し替え点を明確にしている。
  - ロギングを適所に配置し、処理経過・警告・エラーを記録。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 廃止 (Deprecated)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーや Slack トークンなど機密情報は環境変数から取得する設計。デフォルトで .env 自動ロード機能を持つが、CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

注記:
- この CHANGELOG はソースコードからの実装内容を元に作成しています。各機能の利用方法、テーブルスキーマ、外部 API の動作詳細は README または該当モジュールのドキュメントを参照してください。