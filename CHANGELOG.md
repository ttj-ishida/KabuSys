# Changelog

すべての変更は「Keep a Changelog」形式に従い、Semantic Versioning を意識して記載しています。日付・内容はソースコードから推測して作成しています。

## [0.1.0] - 2026-04-02

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ化情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - .env パーサの強化:
      - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの取り扱い、無効行をスキップ。
    - protected セットを用いた .env.local の上書き制御（OS 環境変数保護）。
    - Settings クラスを提供 (settings): 必須キー取得用の _require、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、データベースパス、監視閾値、環境 / ログレベル判定等）。
    - 環境値検証: KABUSYS_ENV / LOG_LEVEL の有効値検査。
- AI モジュール（LLM を用いたニュース解析 / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込むフローを実装。
    - 特徴:
      - タイムウィンドウ計算（JST ベース→UTC 比較）: calc_news_window。
      - 銘柄ごとに記事を結合して文字数トリム（最大記事数・最大文字数制限）。
      - バッチ（デフォルト 20 銘柄）での API 呼び出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
      - JSON 応答の厳密バリデーションとパースフォールバック（余計な前後テキストが混入した場合に最外の {} を抽出して試行）。
      - スコアは ±1.0 にクリップ。
      - DuckDB の executemany に関する互換性問題（空リスト不可）を回避する処理。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - 特徴:
      - ma200_ratio の算出は target_date 未満のデータのみ参照しルックアヘッドを防止。
      - マクロキーワードで raw_news をフィルタしてタイトルリストを作成。
      - OpenAI 呼び出しは最大リトライ回数を設定し、API レスポンスパースエラーや API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
      - 結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試行。
- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー（market_calendar）の夜間バッチ更新ジョブ（calendar_update_job）と営業日判定ユーティリティを実装。
    - 特徴:
      - DB 登録あり → DB 値優先、未登録日は曜日ベースでフォールバック（週末除外）。
      - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
      - 最大探索範囲を _MAX_SEARCH_DAYS で制限して無限ループを防止。
      - バックフィル／健全性チェック（未来日付の異常検出）を実装。
      - J-Quants クライアント経由の差分取得と冪等保存を想定（jq.fetch_market_calendar / jq.save_market_calendar）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインおよび結果データクラス ETLResult を実装（pipeline.ETLResult を etl モジュールで再エクスポート）。
    - 特徴:
      - 差分更新、保存（idempotent 保存を想定）、品質チェック統合を設計方針として実装。
      - ETLResult に品質問題・エラー一覧・集計フィールドを格納し has_errors / has_quality_errors / to_dict を提供。
      - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを実装。
- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算群を実装（momentum / value / volatility / liquidity 関連）。
    - 提供関数:
      - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離 (ma200_dev) を計算（データ不足時は None）。
      - calc_volatility: 20 日 ATR, 相対 ATR (atr_pct), 20 日平均売買代金, 出来高比 (volume_ratio) を計算。
      - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算（未実装項目の記載を明示）。
    - 全て DuckDB の prices_daily / raw_financials を参照し外部発注や本番 API にはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、rank、factor_summary を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。スピアマン係数（ランク相関）や統計サマリーを提供。
- 共通実装
  - DuckDB を想定した SQL 実装（日付操作、ウィンドウ関数、LEAD/LAG 等）を多数導入。
  - OpenAI SDK（OpenAI クライアント）を利用する箇所が存在（api_key パラメータ注入可能でテストが容易）。
  - ロギングが各モジュールで適切に行われる（info/warning/debug/exception）。
  - 各所でルックアヘッドバイアス防止のため datetime.today() / date.today() の無制限使用を回避する設計思想を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
  - ただしソース中に以下の耐障害強化が含まれる:
    - OpenAI API 呼び出しのリトライと 5xx / ネットワークエラーの扱いを明確化。
    - JSON レスポンスのパース失敗時にフォールバックしてスキップするロジック（news_nlp/regime_detector）。
    - DuckDB executemany の空リスト回避。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を protected として扱い、.env による上書きを防ぐ仕組みを導入（安全性向上）。
- API キー（OpenAI など）を関数引数経由で注入可能にしてテスト時に環境変数依存を低減。

---

開発者向けメモ（実装上の注意点・運用ヒント）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などが Settings から要求される（使用箇所に応じて）。
- .env の自動読込はプロジェクトルート検出に依存するため、パッケージ配布後やテスト時に意図した動作にならない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的にロード制御してください。
- OpenAI 呼び出しは外部ネットワークを伴うため、テスト時は kabusys.ai.* の _call_openai_api をモックしてください（コメントでもその想定が明記されています）。
- DuckDB バージョン互換性: executemany に空リストを渡せない点を回避するためのガードが入っています（DuckDB 0.10 系互換を意識）。
- DB 書き込みは冪等化（DELETE → INSERT など）とトランザクション管理（BEGIN / COMMIT / ROLLBACK）を行っています。エラー時はロールバックを試みログ出力します。

もし特定モジュールごと（例: news_nlp の API リトライ挙動、calendar_update_job の J-Quants 呼び出し仕様、research の統計出力形式）の詳細なCHANGELOGやリリースノートが必要であれば、対象モジュールを指定して下さい。