# Changelog

すべての変更は Keep a Changelog の形式に従い記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システムのコアモジュール群を実装しました。

### 追加 (Added)
- パッケージエントリポイント
  - kabusys パッケージの基本情報・公開モジュールを定義（__version__ = 0.1.0、data/strategy/execution/monitoring を公開予定の名前空間として設定）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込み（CWD に依存しない探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント（行頭 #、およびクォートなし値内の "#" 直前の空白でのコメント扱い）に対応。
    - 読み込み時に OS 環境変数は protected として上書きされないよう扱うオプションを実装。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル判定など）。
    - 必須値取得用の _require() を提供し、未設定時は ValueError を送出。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の検証（許容値チェック）を実装。
    - Paper Trading 用の DB パス、PID/KILL フラグなど運用用設定項目を追加。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news と news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをスコア化して ai_scores テーブルへ書き込む機能を実装。
    - ニュース集計ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を算出する calc_news_window を提供。
    - 1銘柄あたり最大記事数・文字数でトリムする保護あり（トークン肥大対策）。
    - 最大 20 銘柄/チャンクでバッチ送信、429/ネットワーク断/タイムアウト/5xx をターゲットに指数バックオフリトライを実装。
    - OpenAI 応答を厳密にバリデーション（JSON 抽出・"results" リスト・code と score の型検査・未知コードの無視・数値チェック）。
    - スコアは ±1.0 にクリップ。
    - 全チャンク処理後に取得できた銘柄のみを置換（DELETE → INSERT）して部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
    - API キーは引数で注入可能（api_key が None の場合は環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError。

- AI 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドを回避。
    - マクロ記事抽出はマクロ関連キーワードでフィルタ（最大 20 記事）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部実装を共有せず結合を防止）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。例外発生時は ROLLBACK を試行し上位に伝播。

- データ処理 / カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を用いた営業日判定ロジックおよび夜間バッチ更新ジョブを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダーがない場合は曜日ベース（土日除外）のフォールバックを行う設計。
    - next/prev_trading_day は最大探索範囲を設定して無限ループを防止。
    - calendar_update_job により J-Quants から差分取得 → save_market_calendar を経て冪等保存。バックフィル・健全性チェックを実装。
    - jquants_client との連携ポイントを用意（fetch_market_calendar / save_market_calendar）。

- ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを実装し ETL 結果の集約と to_dict 出力を提供。
  - pipeline モジュールの ETLResult を etl モジュール経由で再エクスポート。
  - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計文書に準拠した実装方針を反映。

- リサーチツール (kabusys.research)
  - factor_research: Momentum / Volatility / Value / Liquidity 等の定量ファクター計算を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA）を算出。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。必要行数未満は None。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0/欠損は None）。
  - feature_exploration: 将来リターン / IC / 統計サマリーなどを実装。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で算出。horizons の妥当性チェックあり。
    - calc_ic: スピアマン順位相関（ランクベース IC）を実装。データ不足（<3）時は None。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（浮動小数誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - zscore_normalize を含むデータ統計ユーティリティを kabusys.data.stats から再利用して公開。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- ロバストネス向上・フェイルセーフ実装:
  - OpenAI API 呼び出しに対するリトライ/フォールバック動作の明確化（429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ）。
  - OpenAI 応答のパース失敗や不正レスポンスに対して例外を投げずログ出力してフェイルセーフで継続する実装を採用（news_nlp は空結果を返して続行、regime_detector は macro_sentiment=0.0）。
  - DuckDB との互換性考慮（executemany に空リストが渡らないよう事前チェック）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、または ON CONFLICT を想定）。

### 既知の注意点 (Known Issues / Notes)
- 依存:
  - DuckDB、openai パッケージ、J-Quants クライアント実装（kabusys.data.jquants_client）が必要。jquants_client の具体実装は外部連携ポイントとして参照される。
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 機能を利用する場合）は適切に設定する必要があります。Settings._require により未設定時は ValueError が発生します。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数は patch により差し替え可能（ユニットテストでモック化可能）。

### セキュリティ (Security)
- （初版のためセキュリティ修正は無し。API キーやパスワード等は環境変数で管理し、.env の自動ロードを上書き保護する仕組みを提供。）

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装・発注処理との統合・CI テストやドキュメントの充実を予定しています。必要に応じて CHANGELOG を更新します。