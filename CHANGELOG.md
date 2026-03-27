# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠し、セマンティックバージョニングに従います。

全般的な注意
- 日付はリリース日を示します。
- バージョン番号はパッケージ内 `src/kabusys/__init__.py` の `__version__` に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ公開エントリポイントを追加（kabusys/__init__.py）。パッケージは main モジュール群 data, strategy, execution, monitoring を公開する設計を示す。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行い、カレントワーキングディレクトリに依存しない方式を採用。
    - 読み込み優先順序は OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサは以下をサポート・考慮：
    - 空行・コメント行（#）、`export KEY=val` 形式、シングル/ダブルクォートとエスケープ処理、インラインコメントの取り扱い（クォート有無による挙動差）。
    - .env 読み込み時に OS 環境変数（既存キー）を保護するための protected 処理。`.env.local` は上書き可能（override）。
  - Settings クラスを実装し、以下の設定取得アクセサを提供：
    - J-Quants / kabuステーション / Slack / DBパス（DuckDB/SQLite）/ 環境種別（development/paper_trading/live）/ログレベル
    - 必須キー未設定時は `ValueError` を送出（`_require`）。
    - 環境種別・ログレベルは入力値検証を行う（許容値はホワイトリスト）。

- データモジュール（kabusys.data）
  - ETLパイプラインの公開インターフェース `ETLResult` を `kabusys.data.etl` から再エクスポート。
  - pipeline モジュールに ETL 実行ロジックと結果管理を実装（kabusys.data.pipeline）：
    - ETL の差分取得・保存・品質チェックフローを設計文書に準拠して実装。
    - `ETLResult` dataclass を追加（処理各種カウント、品質問題、エラー収集、シリアライズ用 `to_dict` を提供）。
    - DuckDB 上の最終取得日取得ユーティリティなどを実装。
  - カレンダー管理（kabusys.data.calendar_management）を実装：
    - JPXカレンダー（market_calendar）を用いた営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダーが無い場合は曜日（平日＝営業日）ベースのフォールバックを行う設計。
    - 夜間更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。最大探索日数やバックフィル範囲のパラメータを定義。
    - market_calendar の NULL 値に対する警告ログや、最大探索日数 `_MAX_SEARCH_DAYS` による安全策を導入。

- 研究用モジュール（kabusys.research）
  - factor_research: ファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算（EPS が 0 または欠損時は None）。
    - いずれも DuckDB 上の SQL ウィンドウ関数を活用し、ルックアヘッドバイアス防止のため設計に配慮。
  - feature_exploration: 特徴量探索ユーティリティを実装
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（同順位は平均ランク）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 値→ランク変換（同順位に平均ランクを付与、丸め処理で ties の誤検出を抑制）。
  - research パッケージの __init__ で主要関数を公開。`zscore_normalize` は `kabusys.data.stats` から再エクスポートされる想定。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎のセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウは JST 基準で「前日 15:00 JST ～ 当日 08:30 JST」（UTC に変換して DB と比較）。
    - 1 銘柄あたりの上限記事数・文字数（トリム）を導入しトークン肥大化対策を実施。
    - バッチ処理（最大 20 銘柄 / リクエスト）およびエクスポネンシャルバックオフによるリトライ（429/接続断/タイムアウト/5xx）を実装。
    - レスポンスバリデーションを厳格に行い、期待構造（results の配列、code と数値 score）以外はスキップしてフェイルセーフに継続。数値は ±1.0 にクリップ。
    - DuckDB への書き込みは部分置換戦略（DELETE for 対象 code → INSERT）で部分失敗時の既存データ保護を実現。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを用いルックアヘッドを排除。データ不足時は中立（ma_ratio=1.0）。
    - マクロニュース抽出ではマクロキーワード群を用い、対象記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を採用。
    - OpenAI 呼び出しは retry/backoff を実装し、API 失敗時は macro_sentiment=0.0 で継続（例外を上げないフェイルセーフ）。最終的に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - OpenAI 呼び出し部分は外部から差し替えてテスト可能（内部で直接呼び出す関数を分離）。

- OpenAI 統合
  - 両 AI モジュールで OpenAI の Chat Completions（gpt-4o-mini）を JSON mode で利用する設計を採用。
  - API キーは関数引数経由または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を投げる。

### Design / Implementation Notes
- ルックアヘッドバイアス対策
  - いずれのアルゴリズムも内部で `datetime.today()` / `date.today()` を参照せず、明示的な `target_date` を引数にとる設計。
  - DB クエリは target_date 未満／指定レンジを守ることで将来データの不正利用を防止。
- フェイルセーフ設計
  - OpenAI API の失敗やパースエラーは基本的にスキップして処理を継続（データ欠損時のデフォルト値を採用）する方針。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト支援
  - OpenAI 呼び出し関数（内部 _call_openai_api）はユニットテスト時に patch で差し替え可能な位置で実装。

### Changed
- （該当なし／初回リリース）

### Fixed
- （該当なし／初回リリース）

### Security
- （該当なし／初回リリース）

## Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

補足（運用上の注意）
- .env の自動読み込みはプロジェクトルート検出に依存するため、ライブラリを別フォルダにコピーして実行する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト用に別途環境を注入してください。
- OpenAI API の呼び出しは外部サービスに依存するため、APIキーと利用制限（レート制限等）に注意してください。