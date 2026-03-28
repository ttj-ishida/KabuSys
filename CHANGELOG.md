# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、バージョニングは SemVer を採用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システムのコアライブラリとして以下の機能を実装・公開しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開インターフェースの基本 (`__all__`) を定義（data, strategy, execution, monitoring を想定）。

- 環境設定/読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 起点はパッケージファイル位置からプロジェクトルートを探索（.git または pyproject.toml を基準）するため、CWD に依存しない。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
    - OS側の既存環境変数を保護する `protected` の概念を導入。
  - .env パーサを実装（コメント、export 句、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 必須キー未設定時に明確なエラーを投げる `Settings` クラスを提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
  - デフォルト値/検証:
    - `KABUSYS_ENV` の有効値制約（development / paper_trading / live）。
    - `LOG_LEVEL` の有効値制約（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - データベースパスのデフォルト (`DUCKDB_PATH`, `SQLITE_PATH`) を `Path` 型で取得。

- AI（自然言語処理）関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出・`ai_scores` テーブルへ書き込み。
    - バッチ処理、1 API 呼び出しあたりの最大銘柄数は 20（_BATCH_SIZE）。
    - 1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（最大リトライ回数 _MAX_RETRIES）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" 配列の検証、コード正規化、数値変換、スコアのクリップ）。
    - 部分失敗に備え、書き込みは対象コードのみ DELETE→INSERT の冪等置換で実行（DuckDB 互換性に配慮）。
    - テスト容易性のため API 呼び出し箇所を patch 可能に設計（_call_openai_api を差し替え可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・`market_regime` テーブルへ書き込み。
    - マクロキーワードによる raw_news フィルタ、最大 20 記事まで取得、OpenAI（gpt-4o-mini）で JSON 出力を期待（厳格な JSON フォーマット要求）。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ動作。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行。
    - 内部実装でニュースウィンドウ計算は news_nlp の関数を利用（calc_news_window）。

- リサーチ / ファクター群（kabusys.research）
  - factor_research モジュールを実装:
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（calc_momentum）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比（calc_volatility）。
    - バリュー: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials から最新値）（calc_value）。
    - DuckDB を用いた SQL + Python 実装、出力は (date, code) を含む辞書のリスト。
  - feature_exploration モジュールを実装:
    - 将来リターン計算（calc_forward_returns）。デフォルト horizons: [1,5,21]、入力検証（正の整数かつ <=252）。
    - IC（Information Coefficient）計算（calc_ic、Spearman 相当のランク相関）。
    - ランク変換ユーティリティ（rank、同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - research パッケージの public API を整理（zscore_normalize を data.stats から再利用して再エクスポート）。

- データ / ETL（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar）を実装: 営業日判定、next/prev_trading_day、get_trading_days、is_sq_day。
    - DB カレンダーがない場合は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェック、保存件数を返す）。
  - ETL パイプライン基盤（pipeline）
    - 差分取得ロジック、保存、品質チェックを想定した ETLResult データクラスを実装（取得数/保存数/品質問題/エラー一覧を保持）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - etl モジュールは ETLResult を公開エントリとして再エクスポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- 環境変数読み込みで OS 環境を保護（既存の環境変数を上書きしない挙動）をデフォルトにし、必要に応じて .env.local で上書ける仕組みを提供。
- OpenAI API キーの未設定時は ValueError を発生させ安全に明示。

### 開発者向けメモ (Notes)
- 時間に関する設計:
  - ルックアヘッドバイアスを防ぐため、各アルゴリズムは内部で datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取る）。
  - ニュースウィンドウや MA 計算などは UTC naive datetime / date オブジェクトで統一。
- テスト性:
  - OpenAI 呼び出し部はモックしやすいように関数分離（_call_openai_api を patch）してある。
- DuckDB 互換性:
  - executemany の空リストバインド回避や date 型の取り扱いに注意した実装。
- 既知の未実装点:
  - パッケージの __all__ に含まれる strategy / execution / monitoring の具象モジュールや CLI /デプロイ整備は今後のリリースで追加予定。

---

翻訳・実装の解釈に基づいて CHANGELOG を作成しています。追加でリリースノートの粒度（モジュール別の詳細やコミットハッシュ追記など）を指定いただければ、より細かい項目へ分割して更新できます。