# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-09

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ公開
  - パッケージのトップレベルとして kabusys を提供。バージョンは `0.1.0`。
  - __all__ により主要サブパッケージを公開: data, strategy, execution, monitoring（それぞれのサブモジュールは用途別に構成）。

- 環境設定管理 (kabusys.config)
  - Settings クラスを導入し、環境変数ベースで設定値を一元管理。
  - デフォルト値・型チェック・バリデーションを実装（例: KABUSYS_ENV, LOG_LEVEL の許容値チェック、PAPER_FILL_MODE の有効値チェック）。
  - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視関連設定（PID/KILL フラグ、CPU/Memory/Disk 閾値）などをプロパティで提供。
  - .env 自動読み込み機能を実装（優先順位: OS環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込みは既存 OS 環境変数を保護（保護キー集合）し、.env.local は上書き（override）を行う。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ、対応する閉じクォートの検出
    - クォート無し値のインラインコメント処理（直前が空白またはタブの場合のみ '#' をコメントと扱う）
    - 無効行（空行・コメント・`KEY` がない行）は無視

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news および news_symbols を元に銘柄ごとのセンチメントを計算し `ai_scores` テーブルへ書き込む機能を実装。
  - OpenAI（gpt-4o-mini）を JSON Mode（response_format={"type":"json_object"}）で呼び出し、厳密な JSON レスポンスを期待。
  - バッチ処理: 最大 20 銘柄 / API コール（_BATCH_SIZE=20）、1銘柄あたり記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
  - タイムウィンドウ: JST 前日15:00 ～ 当日08:30（内部では UTC naive datetime に変換して比較）。calc_news_window 関数を提供（ユニットテストやルックアヘッド防止目的で日付参照を外部から受ける設計）。
  - 再試行戦略: レート制限(429)、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ（最大 _MAX_RETRIES）。
  - レスポンス検証・整形:
    - JSON パースや `results` リスト、要素の {code, score} 形式を検証
    - スコアを +/-1.0 にクリップ
    - LLM が整数で code を返す場合に備えて str 正規化
    - 部分成功時は成功銘柄のみ `ai_scores` を DELETE→INSERT（部分失敗で既存データを不必要に消さない）
  - フェイルセーフ: API/パース失敗時は該当チャンクをスキップし、処理を継続（例外は上位に伝播させない設計）
  - テスト容易性: OpenAI 呼び出しを差し替え可能（unittest.mock.patch により _call_openai_api をモック可能）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定する機能を実装。
  - ma200_ratio は DuckDB の prices_daily を対象日未満のデータのみで計算（ルックアヘッド防止）。データ不足時は中立 (1.0) とする。
  - マクロニュースは raw_news からマクロキーワードでフィルタ（キーワード一覧を設定）。最大取得記事数は 20。
  - OpenAI 呼び出しは gpt-4o-mini、JSON Mode で行い、失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。リトライ・バックオフ戦略あり。
  - レジームスコア合成式とクリップ、閾値判定（_BULL_THRESHOLD, _BEAR_THRESHOLD）を実装。
  - DB への書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。失敗時は ROLLBACK とエラーハンドリング。

- 研究用ファクター・特徴量（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。欠損は None。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が不適切な場合は None）、ROE を計算。
    - いずれも DuckDB (prices_daily / raw_financials) のみ参照し、本番出荷や発注 API にはアクセスしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons のバリデーション（正の整数 <= 252）。
    - calc_ic: スピアマン（ランク相関）によりファクターの IC を計算（有効レコードが 3 未満で None）。
    - rank: 同順位は平均ランクで扱うランク変換（丸め処理により浮動小数の tie の取り扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median の統計要約を提供。
  - zscore_normalize ヘルパを kabusys.data.stats から再エクスポート。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定と補助関数を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが存在しない場合は曜日ベース（土日を休日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等に更新。バックフィル(日数: _BACKFILL_DAYS=7)、先読み(_CALENDAR_LOOKAHEAD_DAYS=90)、健全性チェック(_SANITY_MAX_FUTURE_DAYS=365) を実装。
  - pipeline / ETL:
    - ETLResult データクラスを実装（target_date, fetched/saved counts, quality_issues, errors 等）。to_dict により品質検査結果を辞書化可能。
    - ETLResult を kabusys.data.etl で再エクスポート。

- DuckDB 互換性と堅牢性
  - DuckDB の executemany で空リストを渡せない制約に配慮した実装（空チェックを行ってから executemany を呼ぶ）。
  - 日付操作はすべて date/datetime オブジェクトで扱い、timezone 混入を防止する設計。
  - ルックアヘッドバイアス防止のため、date.today() / datetime.today() を内部処理で直接参照しない方針（一部関数は引数で基準日を受け取る）。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 削除 (Removed)
- 該当なし（初回リリース）

### 非推奨 (Deprecated)
- 該当なし（初回リリース）

### セキュリティ (Security)
- 該当なし（初回リリース）

---

既知の注記 / 補足
- OpenAI API の呼び出し箇所はテストの容易性を考慮して内部関数をモック可能に設計しています（unittest.mock.patch による差し替え）。
- 一部モジュール（例: strategy, execution, monitoring）はパッケージエクスポートに含まれますが、本 CHANGELOG に記載されたファイル群はデータ取得・研究・NLP・レジーム判定・設定管理に重点を置いた初期基盤実装です。
- 本バージョンは基盤機能の提供に注力しており、本番発注・ブローカー統合等の実装は別モジュールで段階的に追加予定です。