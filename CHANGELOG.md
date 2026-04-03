Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。パッケージの初回リリース v0.1.0 を想定し、コードから読み取れる機能・振る舞いを記載しています。

CHANGELOG.md
=============

すべての変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します（https://keepachangelog.com/ja/1.0.0/）。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース "kabusys"（__version__ = 0.1.0）。
  - k‑abysys パッケージのトップレベル公開モジュール: data, strategy, execution, monitoring。

- 環境設定/ロード機能（kabusys.config）
  - .env ファイルまたは既存の OS 環境変数から設定を自動的に読み込み。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロード（CWD 非依存）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ローダ:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理に対応。
    - クォートなしの値では '#' をインラインコメントとして扱う際の細かい取り扱い（直前が空白またはタブ時にコメント扱い）。
    - override / protected オプションにより OS 環境変数を保護して上書きを制御。
  - Settings クラス:
    - J-Quants / kabuAPI / LINE / DB パス等のプロパティを提供（デフォルト値含む）。
    - 必須環境変数取得時に未設定で ValueError を送出する _require を実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...） のバリデーション。
    - 各種監視設定（PID ファイル、kill フラグ処理・デフォルトパス、閾値 CPU/MEM/DISK）を提供。

- データ基盤ユーティリティ（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーを扱う market_calendar テーブルとの連携。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末は非営業日扱い）。
    - next/prev_trading_day は最大探索日数制限で無限ループを回避。
    - calendar_update_job:
      - J-Quants API から差分取得して market_calendar を冪等更新（fetch -> save）。
      - バックフィル（直近 _BACKFILL_DAYS）の再取得、最新チェック、健全性チェック（過度に未来の日付はスキップ）。
  - ETL パイプライン（pipeline, etl の公開インターフェースを含む）:
    - ETLResult dataclass を公開（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分取得、保存（jquants_client の save_* を想定した冪等保存）、品質チェック呼び出しの設計を反映。
    - DuckDB を用いたテーブル存在チェックや最大日付取得などのユーティリティ。
  - jquants_client との連携を想定（pipeline, calendar_update_job から呼び出し）。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news / news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）に送信しセンチメントを算出。
    - タイムウィンドウ計算（calc_news_window）: JST ベースで「前日 15:00 JST ～ 当日 08:30 JST」を UTC に変換して扱う。
    - 1銘柄あたり最大記事数 (_MAX_ARTICLES_PER_STOCK) と最大文字数 (_MAX_CHARS_PER_STOCK) でプロンプト肥大化を制限。
    - バッチ処理: 最大 _BATCH_SIZE（20） 銘柄ごとに API コール。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライ（リトライ上限あり）。
    - レスポンス検証: JSON の抽出/パース、"results" リストの形式検証、コード照合、スコア数値性と有限性検査。スコアは ±1.0 にクリップ。
    - DB 書き込み: ai_scores テーブルへは取得したコードのみを削除→挿入する方式で部分失敗時の既存データ保護（DuckDB executemany の空リスト注意を反映）。
    - テスト容易性: _call_openai_api をテストでモック可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルに書き込み。
    - マクロニュース収集は news_nlp.calc_news_window と raw_news のマクロキーワードフィルタにより行う。
    - OpenAI 呼び出しは JSON 出力を期待し、レスポンスパース失敗や API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - スコア合成後、閾値に基づいて regime_label を bull/neutral/bear と決定。
    - DB 書き込みはトランザクショナル（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行して例外伝播）。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: latest 財務データ（raw_financials）を使って PER（close / EPS、EPS=0または欠損時は None）と ROE を計算。
    - 実装は DuckDB の SQL ウィンドウ関数等を多用して高速に計算、外部 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の妥当性チェック有り。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード数が 3 未満の場合は None を返す。
    - rank: 同順位は平均ランク扱い（丸めで ties 検出の安定化）。
    - factor_summary: 指定カラム群について count/mean/std/min/max/median を計算（None を除外）。
  - 研究用ユーティリティの公開（zscore_normalize の再エクスポートを含む）。

Other notable behaviors / design decisions
- ルックアヘッドバイアス回避:
  - 多くのモジュールで datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満/未満等の排他条件で未来データ参照を回避。
- フェイルセーフ設計:
  - AI API 呼び出し失敗時にはゼロや空の結果で継続する（重大な例外を投げず処理を保護）。
  - DB 書き込みは冪等化・トランザクション化され部分失敗の影響を最小化。
- テストフレンドリー:
  - OpenAI 呼び出しをラップする内部関数をモック可能にしてユニットテストを容易にしている。
- DuckDB を主データストアとして利用する前提で SQL と Python を組み合わせた実装。

Known issues / Limitations
- monitoring モジュールが __all__ に含まれているが、今回提供されたコード断片内に実装ファイルは含まれていません（将来追加想定）。
- 一部外部依存（openai ライブラリ、jquants_client）の具体的実装はこのスナップショットに含まれておらず、統合テスト時に接続情報や API キー（OPENAI_API_KEY 等）が必要です。

Notes
- 本 CHANGELOG は与えられたコードベースからの推測に基づいて作成しています。リリースノートとして公開する場合は実際のリリース日、責任者、追加の破壊的変更 (BREAKING CHANGES) 情報などを追記してください。