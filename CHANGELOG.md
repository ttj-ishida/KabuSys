# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。  

リリースのセマンティクスは SemVer に従います。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env および .env.local からの自動設定読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - エクスポート形式（export KEY=val）やクォート・エスケープ・インラインコメント処理など、.env の堅牢なパーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト等で使用可能）。
  - 必須変数取得ヘルパー _require を提供し、未設定時に明確なエラーメッセージを返す。
  - 各種設定プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定など）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装。
  - PID / kill フラグ、CPU/メモリ/ディスク閾値など監視用設定を追加。

- AI（自然言語処理）機能
  - kabusys.ai.news_nlp: ニュース文章を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとの ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、銘柄ごとの記事集約、最大トークン対策（記事数・文字数トリム）。
    - バッチ（最大 20 銘柄）単位での API 呼び出し、JSON Mode 利用、レスポンス検証、スコアクリップ（±1.0）。
    - レート制限・ネットワーク障害・5xx に対する指数バックオフリトライの実装。
    - DuckDB の executemany に関する互換性（空リスト回避）に配慮した DB 書き込み（DELETE → INSERT の冪等処理）。
    - テスト容易性のため OpenAI 呼び出し箇所に差し替え可能ポイントを用意（unittest.mock.patch 用）。
  - kabusys.ai.regime_detector: ETF 1321（Nikkei 225 連動 ETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能を実装。
    - ma200_ratio 計算（lookahead 回避のため target_date 未満のみ使用）、マクロキーワードによる記事抽出、LLM 呼び出し（gpt-4o-mini）、結果合成とクリップ処理。
    - LLM エラー時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 呼び出しの再試行と 5xx 区別、JSON パース失敗時のログとフォールバックを実装。

- データ基盤（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理モジュールを追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録ありの場合は DB 値優先の一貫したロジックを実装。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィル・健全性チェック含む）するバッチ処理を実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開し、ETL の標準的な結果格納フォーマット（取得数・保存数・品質問題・エラー一覧など）を定義。
    - 差分更新・バックフィル・品質チェックの方針を反映した ETL 基盤（jquants_client 経由の差分取得と idempotent 保存想定）。

- 研究機能（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率等を計算。
    - calc_value: raw_financials から最新財務情報を取得して PER / ROE を計算（EPS 0/欠損時は None）。
    - 設計上、DuckDB 接続を受け取り SQL ベースで完結（外部 API へアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定基準日から将来リターン（horizons）を一括取得する SQL 実装。horizons バリデーションあり。
    - calc_ic: スピアマンランク相関による IC 計算を実装（NA や同値の扱いに配慮）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出するユーティリティを実装。
    - 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで完結。

### 変更 (Changed)
- （初回リリースのため過去変更はなし）

### 修正 (Fixed)
- （初回リリースのため過去修正はなし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能にし、環境変数依存を緩和。未設定時は ValueError で明示的に通知。

### 設計上の留意点・重要事項
- ルックアヘッドバイアス防止:
  - ニュース・レジーム・ファクター計算全てで datetime.today()/date.today() を直接参照せず、外部から与えられる target_date のみを基準に処理する設計。
  - prices_daily クエリは target_date 未満 / 等の条件でルックアヘッドを防止。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを中立（0.0）にフォールバックする等、例外を上位に伝播させず継続する実装箇所がある（ただし DB 書き込み失敗時は例外伝播）。
- テスト容易性:
  - OpenAI 呼び出し箇所に差し替えフックを用意（unittest.mock.patch によるモック化を意識）。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン問題への対応（空チェックを行ってから executemany 実行）。

---

このバージョンは初期の機能実装を幅広く含むため、今後のリリースで以下のような改善・拡張が想定されます：
- strategy / execution / monitoring モジュールの具体的な発注ロジック・稼働監視機能の実装
- より詳細な品質チェックルールやアラート機能
- OpenAI モデルやプロンプトの改善、レスポンス検証の強化
- パフォーマンス最適化と大規模データ対応

ご要望があれば、各機能の変更履歴をより細かく（関数単位・コミット単位）で記載することも可能です。