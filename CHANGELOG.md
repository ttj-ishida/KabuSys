# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-03-26

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義。
  - 公開インターフェースに data, strategy, execution, monitoring を含む。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイル自動読み込み機能を実装（OS環境変数優先、.env.local は上書き）。
  - 環境変数読み込みの自動無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .git または pyproject.toml を起点にプロジェクトルートを探索して .env を検出することで CWD に依存しない動作を実現。
  - .env のパースロジックを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの取り扱い（クォート外で直前がスペース/タブの `#` をコメントとして扱う）
  - OS 環境変数を保護する protected セットの仕組み（override=True 時に上書き禁止）。
  - 必須環境変数取得ヘルパー _require と、アプリ設定 Settings クラスを提供（各種必須キーのプロパティを持つ）。
  - 設定検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許可
    - LOG_LEVEL は標準ログレベルのみ許可

- ニュース NLP / AI
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信してセンチメント（ai_score）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（JST 基準: 前日 15:00 ～ 当日 08:30）を計算する calc_news_window 実装。
    - バッチサイズ・トークン肥大化対策（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON パース回復処理、results フィールド検証、未知コード無視、数値化・有限性チェック、スコア ±1.0 クリップ）。
    - DuckDB 0.10 の executemany の挙動に配慮（空リスト処理を回避）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタリングし、最大 _MAX_MACRO_ARTICLES 件を LLM に送信。
    - OpenAI 呼び出しに対するリトライ・5xx 判定や API エラー処理を実装。API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア計算後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため独立した _call_openai_api を使用（news_nlp と共有しない設計）。

- リサーチ（研究）モジュール (kabusys.research)
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - Value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS=0 の場合は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。
    - すべて DuckDB の SQL と組み合わせて実行（外部 API を呼ばない）。
  - 特徴量探索: calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、rank（平均ランク同順位処理）、factor_summary（統計サマリー）を実装。
    - calc_forward_returns は任意ホライズンに対応、入力検証（正の整数かつ <= 252）を実施。
    - calc_ic は有効レコードが 3 件未満なら None を返す。
  - kabusys.research パッケージで zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム / ETL (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末除外）を採用して一貫性を保持。
    - next/prev_trading_day は最大探索日数を設けて無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル・保存を実行（健全性チェック付き）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL 結果の集約、品質問題やエラーを保持）。
    - 差分取得・保存・品質チェックのための基盤ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - デフォルトの backfill 挙動・カレンダー先読み等の設計方針を実装。
  - jquants_client への呼び出しを想定した設計（fetch/save の呼び出しポイントを確保）。

### 変更 (Changed)
- 設計方針の明文化:
  - 主要な AI / 研究 / データ処理関数は datetime.today()/date.today() に直接依存しない設計（呼び出し側が target_date を渡す）に統一。ルックアヘッドバイアス防止を明確化。
  - DuckDB の互換性問題（executemany の空リスト等）に対応する実装上の配慮を導入。
  - OpenAI 呼び出しの失敗時のフェイルセーフ（スコア 0.0、または処理スキップ）を徹底。

### 修正 (Fixed)
- 環境変数パーサーの堅牢化:
  - 引用符内のバックスラッシュエスケープ、クォート閉じの検出、無効行の扱いなど、.env の境界条件を取り扱うよう改善。
- AI モジュールのエラーハンドリング改善:
  - JSON パース失敗時に余分な前後テキストを切り出して復元する試みを追加（JSON Mode でも前後ノイズが混じるケースへの対応）。
  - OpenAI API エラー種別ごとにリトライ判定を実装（RateLimitError/APIConnectionError/APITimeoutError はリトライ、APIError は status_code によって 5xx のみリトライ等）。

### 既知の注意点 (Known issues / Notes)
- OpenAI API キーが未設定の場合、news_nlp.score_news および regime_detector.score_regime は ValueError を送出する。テスト時は api_key を引数で注入するか環境変数 OPENAI_API_KEY を設定すること。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（パッケージ配布環境などでの注意）。
- DuckDB の日付型や戻り値は date オブジェクトに変換して扱う実装を行っているが、環境や DuckDB バージョンによっては注意が必要。

### 廃止 / 削除 (Deprecated / Removed)
- なし

### セキュリティ (Security)
- なし

---

今後のリリースでは、strategy / execution / monitoring の詳細実装や CI テストケース、より詳細な品質チェックルール、モデルプロンプト改善・評価基盤の追加などを予定しています。