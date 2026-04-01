# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- 今後のリリースに向けた作業項目や既知の改善点をここに記載します。

## [0.1.0] - 2026-04-01
初期リリース。

### 追加 (Added)
- パッケージ構成
  - kabusys コアパッケージを公開 (サブパッケージ: data, research, ai, config, （実行/監視用プレースホルダ: execution, monitoring）)。
  - バージョン情報: `__version__ = "0.1.0"`。

- 設定管理
  - 環境変数からの設定読み込み機能を実装（src/kabusys/config.py）。
  - プロジェクトルートを .git または pyproject.toml から自動検出し、プロジェクト内の .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - `.env` 解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどを正しく扱う堅牢なパーサを実装。
  - 既存の OS 環境変数を保護するため protected set を用いた上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / 環境・ログレベルなどの取得とバリデーションを行うプロパティを実装。無効な env 値は例外を発生させる。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン用のデータ構造とユーティリティ（ETLResult、pipeline モジュールの公開インターフェース）。
  - calendar_management モジュールを実装（JPX カレンダー管理、market_calendar テーブルの夜間バッチ更新、営業日判定ユーティリティ）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 未取得日は曜日ベース（土日非営業）でフォールバックする設計。
    - calendar_update_job による差分取得・バックフィル・健全性チェックを実装。
  - ETL の設計方針を反映: 差分更新・バックフィル・品質チェック（quality モジュールとの連携を想定）・冪等保存（ON CONFLICT 相当）をサポート。

- AI（OpenAI 統合）
  - ニュース NLP スコアリング: `score_news`（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数/文字数上限、レスポンス検証、スコアクリップ（±1.0）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、その他はスキップして継続するフェイルセーフ設計。
    - DuckDB への置換的書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の既存データ保護。
    - テスト容易性のため _call_openai_api をパッチ可能（unittest.mock.patch を想定）。
  - 市場レジーム判定: `score_regime`（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して当日の市場レジーム（bull/neutral/bear）を算出・保存。
    - マクロニュース取得は news_nlp の calc_news_window を利用し、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、リトライ・エラーハンドリングを行う。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
  - 共通の設計指針:
    - レスポンスは厳密な JSON を期待するが、パースエラー時は安全にフォールバックして処理継続。
    - ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。

- リサーチ / ファクター計算
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供。
    - データ不足時の None ハンドリング、返却は (date, code) を含む dict リスト。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - pandas 等外部依存なしで純粋 Python + DuckDB SQL による実装。
  - research パッケージで主要関数を再エクスポートし、研究用途に使いやすく提供。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- ニュース / レジーム判定系の堅牢化
  - OpenAI レスポンスの JSON パース失敗時に、文字列中の最外側の {} を抽出して復元する試みを実装。
  - API エラー（5xx）とそれ以外のエラーで処理を分岐し、適切にリトライまたはスキップするようにした。
- DuckDB への複数行操作についての互換性処理
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約回避）。

### セキュリティ (Security)
- 環境変数の自動読み込み時に OS 環境変数を保護（.env による上書きを防ぐオプション）する設計を導入。
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から解決。未設定時は明確な ValueError を発生させることで誤用を防止。

### 破壊的変更 (Breaking Changes)
- 初期リリースのため、後続バージョンでの設計変更に注意。ただし以下の挙動は仕様として注意点あり:
  - AI 関連関数は target_date を必須にしており、内部で現在時刻を参照しないため呼び出し側で正しい日付を与える必要がある（ルックアヘッド保護）。
  - OpenAI API キーが未指定の場合は ValueError を送出するため、運用時には環境変数または引数でキーを指定すること。

### 既知の制約 / 今後の改善候補
- execution / monitoring モジュールの公開はパッケージ __all__ に含まれているが、今回のスナップショットには実装コードが含まれていない（将来の実装予定）。
- ai モジュールは外部 API（OpenAI）に依存するため、API仕様変更やレート制限に対するさらなる堅牢化（キューイング、コスト制御等）が検討対象。
- quality モジュールの具体的なチェックの運用方針やアラート連携は今後拡充予定。

---

作成: 自動生成（コードベースの内容から推測）。必要であれば、リリースノートの粒度（関数単位の変更履歴、コミット単位のログなど）を細かく作成します。どのレベルの詳細が必要か教えてください。