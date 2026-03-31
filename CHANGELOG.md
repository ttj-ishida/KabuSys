# Keep a Changelog
すべての重要な変更点をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-31
初回リリース。本バージョンでは日本株自動売買システムのコア機能群を実装・公開します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して決定（CWD 非依存）。
  - .env / .env.local 読み込みの優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは export 形式、クォート内のエスケープ、インラインコメント扱い、空行/コメント行無視等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境種別（development/paper_trading/live）等の取得を型安全にラップ。必須変数未設定時は ValueError を送出。

- AI（自然言語処理）関連 (kabusys.ai)
  - news_nlp（score_news）
    - raw_news と news_symbols を集計して銘柄ごとにニューステキストを結合し、OpenAI（gpt-4o-mini の JSON mode）へバッチ送信してセンチメントスコアを生成。
    - バッチ単位、トークン肥大化対策（銘柄ごと記事数上限／文字数上限）、最大同時銘柄数（_BATCH_SIZE）等を考慮。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップを実装。
    - DuckDB への書き込みは冪等性を意識（取得済みコードのみ DELETE → INSERT）し、部分失敗時の既存データ保護に配慮。

  - regime_detector（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と macro ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
    - LLM 呼び出しに対するリトライ、API エラー時の安全フォールバック（macro_sentiment=0.0）を実装。
    - DB クエリはルックアヘッドを防ぐため target_date 未満のデータのみを使用。
    - market_regime テーブルへの書き込みは BEGIN / DELETE / INSERT / COMMIT による冪等性を確保。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ (calendar_update_job) を実装。J-Quants クライアント経由で差分取得し、market_calendar を冪等更新。
    - 営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が欠けている場合は曜日（平日）ベースでフォールバック。DB に断片的にデータがある場合でも一貫した判定となるよう設計。
    - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装。

  - pipeline / etl
    - ETLResult 型を実装して ETL パイプライン結果（取得数・保存数・品質問題・エラー等）を一元管理。
    - データ差分取得・保存・品質チェックを行う設計（J-Quants API と品質チェック quality モジュールと連携する想定）。
    - DuckDB 互換性を意識した実装（executemany の空リスト回避など）。

- 研究用ユーティリティ (kabusys.research)
  - factor_research
    - Momentum, Value, Volatility, Liquidity 等のファクター計算実装:
      - calc_momentum: 1M/3M/6M リターン・200 日 MA 乖離（ma200_dev）
      - calc_value: PER, ROE（raw_financials と prices_daily を結合）
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高変化率
    - DuckDB を用いた SQL ベースの実装でルックアヘッド回避。
  - feature_exploration
    - calc_forward_returns: 将来リターン（LEAD を用いたホライズン別計算）
    - calc_ic: スピアマンのランク相関（IC）計算
    - rank, factor_summary: ランク化、基本統計量計算を実装
  - data.stats の zscore_normalize を re-export

- 実運用配慮
  - 全体的に datetime.today() / date.today() の直接参照を避け、関数呼び出し側から target_date を与える設計でルックアヘッドバイアスを防止。
  - OpenAI 呼び出しは各モジュールで独立実装し、テスト時に差し替え可能（ユニットテスト用の patch 想定）。
  - ロギング・リトライ・フェイルセーフ（API 失敗時のフォールバック）を広範に実装。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の問題 (Known issues)
- data.pipeline._get_max_date 実装の途中でコードが途切れている様子（末尾に誤った "date.fro" が存在）：
  - 現状ではこのヘルパーが未完のため、この関数に依存する処理で NameError / SyntaxError が発生する可能性があります。リリース直後にパッチが必要です。
- DuckDB バインディングやバージョン差分に起因する注意点:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮したコードパスを一部実装しているが、環境によっては追加検証が必要。
- OpenAI 統合の挙動:
  - JSON mode を前提としたレスポンス処理は堅牢化しているが、予期しないレスポンスフォーマットに対しては安全にスキップする設計（スコアを返さない・0.0 でフォールバック）となっている。運用では API キーやレート制限に注意。

### セキュリティ (Security)
- 設定の扱い:
  - 機密情報（API キー、パスワード等）は環境変数経由で取得する設計。必須変数未設定時は早期に例外を投げることで誤った運用を防止。
  - .env 読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

---

今後のリリースでは下記を予定しています（予定項目、実装順序・内容は変更される可能性があります）:
- pipeline._get_max_date の修正と ETL 実行フローの統合テスト
- strategy / execution / monitoring の具体的な注文・監視ロジックの実装とテスト
- 追加的な品質チェックルールと監査ログの強化
- ドキュメント（API 仕様・運用手順・環境構築手順）の拡充

ご要望があれば、既知の問題の修正用パッチ案や個々のモジュールの詳細な変更履歴（コミット単位の推定）も作成します。