# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ (0.1.0) に合わせています。

## [Unreleased]

（現在リリース予定なし）

## [0.1.0] - 2026-04-04

Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring をパッケージトップから公開。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイル自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は .env を上書きする。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサ実装の強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォート無しの行では '#' をインラインコメントとして扱うルール（直前がスペースまたはタブの場合のみ）。
  - 上書き制御: override 引数、protected（OS 環境変数を凍結）により安全な読み込みを保証。
  - Settings クラスを提供し、環境変数をプロパティとして取得可能に:
    - J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / システム設定（env, log_level）等のプロパティを提供
    - 必須のキーは _require() で検証し、未設定時には ValueError を送出
    - KABUSYS_ENV の許容値は {development, paper_trading, live}
    - LOG_LEVEL の許容値は {DEBUG, INFO, WARNING, ERROR, CRITICAL}
    - is_live / is_paper / is_dev の便宜プロパティを追加

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価する処理を実装。
  - 時間ウィンドウ: JST 基準で「前日15:00～当日08:30」を対象（内部は UTC naive datetime）。
  - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）まで処理。
  - 1 銘柄あたりの制約: 最大記事数 _MAX_ARTICLES_PER_STOCK（既定10）、最大文字数 _MAX_CHARS_PER_STOCK（既定3000）でトリム。
  - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ（最大回数設定あり）。
  - レスポンス検証: JSON パース、"results" リスト、各要素に code/score を要求、未知コードは無視、数値チェック、±1.0 にクリップ。
  - DB 書き込み: ai_scores テーブルへは取得済みコードのみ置換（DELETE → INSERT）し、部分失敗時に既存のスコアを保護。
    - DuckDB の executemany の制約に配慮して、空リスト時の呼び出し回避を実装。
  - テストしやすさ: OpenAI 呼び出し箇所は _call_openai_api を分離しており、ユニットテストで patch 可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
  - マクロニュース抽出はマクロキーワードリストに基づき raw_news からタイトルを取得し、LLM（gpt-4o-mini）で JSON 出力を期待。
  - OpenAI 呼び出しは再試行・エラー分類を実装し、API 失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
  - スコア合成時にクリップ・閾値でラベリングし、market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に保存。
  - テスト用に OpenAI 呼び出し関数はモジュール間で共有せず分離。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR(atr_pct)、20 日平均売買代金、出来高比率を計算。データ不足に対する None 表現。
    - calc_value: raw_financials から最新の財務データ（report_date <= target_date）を取り、PER / ROE を計算（EPS 無効時は None）。
    - DuckDB 上で SQL + Python 組合せにより実装（外部 API や発注ロジックにアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（ランクは同順位の平均ランクを採用）を計算。有効レコードが 3 件未満なら None。
    - rank: 値リストをランクに変換（round(...,12) により浮動小数丸め誤差対策）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
  - すべて標準ライブラリ中心で実装し pandas などを依存しない設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー取得・管理用ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev_trading_day は DB 登録があれば優先的に使用し、未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job: J-Quants クライアント経由で差分取得 → jq.save_market_calendar により冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - ETL の設計方針（差分更新、backfill、品質チェックの振る舞い）をコード内に反映。
    - DuckDB の存在チェックや最大日付取得などユーティリティを実装。

Other
- DuckDB を主要なローカル分析データベースとして使用する前提で SQL 実装。
- OpenAI SDK（OpenAI client）を直接利用する実装（APIキー注入可）。
- ロギングを各モジュールに導入し、警告・情報出力を充実。
- 失敗からのフェイルセーフ設計（外部 API 呼び出し失敗時はスキップして処理継続、DB 書込失敗時は ROLLBACK を実施して上位へ例外伝播）。

Notes / Implementation details
- OpenAI のモデルと JSON Mode を使うため、レスポンスパースのロバストネス（前後余計なテキストのトリムなど）を実装。
- AI モジュールはテスト容易性を考慮して _call_openai_api を分離しているため、ユニットテストで差し替え可能。
- DuckDB の executemany の挙動（空リストバインド不可等）に対するガードを実装。
- 日付扱いはすべて datetime.date / datetime に統一し、タイムゾーン混入を避ける設計。

---

（初期リリースのため Added の記述が中心です。将来的なバージョンでは Changed / Fixed / Deprecated などを追加していきます。）