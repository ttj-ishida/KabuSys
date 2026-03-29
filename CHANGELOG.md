# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  
現在のリリースポリシー: 主要/マイナー/パッチのセマンティックバージョニング。

## [0.1.0] - 2026-03-29

初回リリース。以下の主要機能と実装を含みます。

### 追加 (Added)
- パッケージの公開インターフェース
  - パッケージバージョン: kabusys.__version__ = "0.1.0"
  - パッケージ外部公開名前空間: __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読込する仕組みを実装。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を検索（配布後の動作安定化）。
  - .env パーサー強化:
    - コメント行・空行無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - クォートなし値のインラインコメント認識（直前がスペース・タブの場合）。
  - 読み込み優先度: OS 環境 > .env.local > .env (.env.local が上書きする)。OS 環境のキーは保護（上書きされない）。
  - Settings クラスを導入し、環境依存の設定値をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として _require() で検証。
    - KABUSYS_ENV 値検証: development / paper_trading / live のみ許容（不正な値は ValueError）。
    - LOG_LEVEL 検証: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
    - DB パス設定: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチ・チャンク処理: 最大 _BATCH_SIZE（20） 銘柄ずつ送信。
    - 1銘柄あたり最大記事数 (_MAX_ARTICLES_PER_STOCK=10) / 最大文字数 (_MAX_CHARS_PER_STOCK=3000) でトリム。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、"results" リスト、各要素の code/score 検査、未知コードは無視、スコアを ±1.0 にクリップ）。
    - 書き込み: 成功した銘柄分のみ ai_scores テーブルを置換（DELETE → INSERT）。DuckDB の executemany に対する互換性（空リスト回避）に配慮。
    - テスト容易性: OpenAI 呼び出しは _call_openai_api を patch して差し替え可能。
    - score_news は書き込んだ銘柄数を返す。

  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の算出は target_date 未満のデータのみを使用しルックアヘッドを防止。データ不足時は中立（1.0）にフォールバックして警告ログ。
    - マクロニュース抽出はキーワード絞り込み（複数キーワード定義）し最大 20 件まで採取。
    - LLM 呼び出しは gpt-4o-mini / JSON Mode、失敗時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - レジームスコア合成と閾値判定（BULL_THRESHOLD/BEAR_THRESHOLD）、結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは retries/backoff を備え、APIError の status_code による再試行判定を実装。
    - テスト容易性: _call_openai_api を patch で差し替え可能。

- データ / ETL / カレンダー (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照する is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 登録がない日や NULL は曜日ベースのフォールバック（週末＝非営業日）で一貫した挙動を返す。
    - 最大探索日数の上限 (_MAX_SEARCH_DAYS=60) を設け、無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client）から差分でカレンダーを取得して market_calendar に保存するバッチ処理を実装。
      - バックフィル (_BACKFILL_DAYS=7)、先読み (_CALENDAR_LOOKAHEAD_DAYS=90)、健全性チェック (_SANITY_MAX_FUTURE_DAYS=365) を実装。
      - API エラーや取得ゼロ時は 0 を返す安全設計。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーリスト等を保持）。
    - 差分更新・バックフィル・品質チェックの設計に対応するユーティリティ関数（_get_max_date, _table_exists など）。
    - J-Quants クライアント（jquants_client）経由でのデータ取得と idempotent 保存を想定。
    - 品質チェックの結果は ETLResult に集約し、呼び出し元が対処を決定可能（Fail-Fast しない）。

- 研究モジュール (kabusys.research)
  - ファクター計算群を提供（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）・相対ATR（atr_pct）・20日平均売買代金（avg_turnover）・出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損なら PER=None）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の入力検証あり（1〜252 の整数）。
    - calc_ic: スピアマン（ランク）による IC 計算（十分な有効レコードがない場合は None）。
    - rank: 同順位は平均ランクで処理（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を標準ライブラリのみで計算。
  - 研究 API の一部を __all__ で再エクスポート（zscore_normalize 等は kabusys.data.stats から利用）。

### 変更 (Changed)
- 初版のため特段の互換性変更はなし（将来のバージョンで API 変更の可能性あり）。

### 修正 (Fixed)
- 初版のため該当なし。

### 注意点 / 実装上の補足
- ルックアヘッドバイアス対策:
  - 各種処理（news_nlp, regime_detector, research）で内部的に datetime.today() / date.today() を直接参照せず、引数として与えられる target_date に対して厳密に過去データのみを参照するよう設計。
- DB 書き込みは冪等性を重視:
  - market_regime / ai_scores 等は該当日とコードで既存行を削除してから挿入することで、複数回実行しても一貫した状態を保つ設計。
- フェイルセーフ:
  - LLM/API の失敗は例外を即座に投げず（多くの箇所で）スコア 0.0 または空スコアとしてフォールバックすることで、上位処理が継続できるようにしている。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーとなるバージョンがあるため、空チェックを行ってから executemany を呼ぶ実装とした。
- テスト容易性:
  - OpenAI 呼び出しを内部関数（_call_openai_api）でラップしてあり、unit test で patch により差し替え可能。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が必須（Settings のプロパティで検証）。不足時は ValueError が発生。

### 既知の制約 / TODO
- 一部のモジュールは将来の拡張（PBR・配当利回り等の実装、strategy/execution/monitoring の実装）を想定しているが、現バージョンでは未実装。
- ETL パイプラインの高レベル制御や scheduler 連携は利用側で実装する必要がある。
- jquants_client の具体実装は外部モジュール（kabusys.data.jquants_client）に依存するため、環境に応じたクライアント実装が必要。

---

今後のリリースでは下記のような変更を想定しています:
- strategy/execution モジュールの実装と実注文まわりの安全機構
- 監視・アラート機能（Slack 通知の統合）
- 性能改善（バッチ並列化、DuckDB クエリ最適化）
- CI テストの充実（OpenAI モック、DuckDB テストフィクスチャ）

署名: kabusys 開発チーム