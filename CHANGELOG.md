# Changelog

すべての注目すべき変更を記録します。本来は Keep a Changelog のフォーマットに準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]

## [0.1.0] - 2026-04-09
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。公開モジュールとして data, strategy, execution, monitoring をエクスポートする旨を定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動 .env 読み込みを実現。
  - .env のパースは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - 行内コメントの取り扱い（クォート外でかつ直前が空白／タブの場合）
  - .env と .env.local の読み込み順序と上書きルール（OS 環境変数保護）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、J-Quants や kabu API、LINE、DB パス、Paper Trading、監視閾値、環境（development/paper_trading/live）やログレベル等のプロパティを提供。
  - 各プロパティにバリデーションとデフォルト値を付与（例: PAPER_FILL_MODE の許容値チェック、LOG_LEVEL/ KABUSYS_ENV の検証）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集計し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）へ送信しセンチメントを取得する処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - チャンク処理（最大 20 銘柄 / バッチ）、1 銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフの実装。
    - OpenAI の JSON Mode に対するレスポンス検証ロジック（JSON パース、results フィールド検査、コード照合、数値検証、スコアの ±1.0 クリッピング）。
    - DuckDB への冪等書き込み（DELETE → INSERT の形）により部分失敗時に既存スコアを保護。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。未設定時は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する実装。
    - ma200_ratio の算出（target_date 未満のデータのみ使用してルックアヘッド防止）、データ不足時の中立扱い（1.0）と警告ログ。
    - マクロニュース抽出（タイトルベースでマクロキーワードにマッチする記事を取得）と最大取得件数制約。
    - OpenAI 呼び出しのリトライ、エラー種別ごとの扱い（5xx は再試行、非5xx はフォールバック）、パース失敗や API エラー時のフェイルセーフ（macro_sentiment=0.0）。
    - スコア合成、閾値でラベル決定、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理と警告ログ）。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。未設定時は ValueError を送出。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（mom_1m, mom_3m, mom_6m）、200 日移動平均乖離（ma200_dev）を calc_momentum で実装。データ不足時は None を返す設計。
    - ボラティリティ / 流動性（calc_volatility）: 20 日 ATR（atr_20/atr_pct）、20 日平均売買代金、出来高比率等を計算。計算に必要な行数が不足する場合は None を返す。
    - バリュー（calc_value）: raw_financials から直近の財務データを取得して PER / ROE を計算。EPS が 0/欠損時は PER を None に。
    - DuckDB を用いた SQL 中心の実装で外部 API 呼び出しを行わない設計。

  - 特徴量探索 / 統計（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（営業日ベース）に対する将来リターンを一括で取得。horizons のバリデーション（正の整数かつ <=252）を実装。
    - IC（Information Coefficient）計算（calc_ic）: factor_records と forward_records を code で結合してスピアマンの順位相関を算出。データ不足（有効レコード < 3）時は None を返す。
    - ランキングユーティリティ（rank）: 同順位は平均ランクで扱い、浮動小数丸め誤差対策として round(..., 12) を使用。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。None 値を除外。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を参照して営業日判定（is_trading_day）、SQ 判定（is_sq_day）、前後営業日の探索（next_trading_day / prev_trading_day）、指定期間の営業日リスト取得（get_trading_days）を実装。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 探索は _MAX_SEARCH_DAYS による上限を設け、無限ループを防止。
    - calendar_update_job により J-Quants API（jquants_client）からの差分取得、バックフィル、健全性チェック、冪等保存を実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass を導入し、ETL の取得件数・保存件数・品質チェック結果・エラー一覧などを集約して返却可能に。
    - pipeline モジュール（概要）: 差分取得、idempotent な保存（jquants_client.save_*）、品質チェック（quality モジュール）を行う方針を実装。
    - デフォルトのバックフィル動作やカレンダープロセス連携など ETL 実装の設計方針を反映。
    - kabusys.data.etl で ETLResult を再エクスポート。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Notes / 実装上の重要な設計決定
- ルックアヘッドバイアス防止:
  - 多くの処理で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計を採用。
  - DB クエリでは target_date 未満 / 指定範囲の排他条件で将来データ参照を防止。
- OpenAI 呼び出し:
  - GPT モデル（gpt-4o-mini）を JSON mode で利用。API レスポンスの堅牢な検証とフェイルセーフ（失敗時に 0.0 やスキップ）を実装。
  - テストの容易性を考慮し、_call_openai_api をパッチ可能にしている。
- DB 書き込み:
  - 重要処理は BEGIN/COMMIT/ROLLBACK を使用した冪等性確保のパターンを採用。部分失敗時に既存データを不必要に削除しないよう設計。
- DuckDB 互換性:
  - executemany の空リスト禁止など DuckDB の実装差分を考慮した実装上の注意が各所に反映されている。

もし特定モジュールの変更履歴をもっと詳細に分けたい、あるいは将来のリリース向けに Unreleased に追加したい項目があれば教えてください。