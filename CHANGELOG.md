# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム KabuSys のコアライブラリを公開しました。以下の主要機能と設計方針を実装しています。

### Added
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ にてエクスポート）

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能（テスト用途向け）
  - 詳細な .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープを処理
    - クォートなし行のインラインコメント取り扱いルール
  - 必須環境変数取得用の _require() 実装（未設定時は ValueError を送出）
  - 設定値検証:
    - KABUSYS_ENV: development / paper_trading / live のみ許容
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容
  - データベースパス取得ユーティリティ（duckdb_path, sqlite_path）

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)
      - 前日 15:00 JST 〜 当日 08:30 JST の記事を対象に銘柄別にセンチメントを生成し ai_scores テーブルへ書き込み
      - ニュース集約、1銘柄あたり記事数・文字数トリム、最大バッチサイズで OpenAI に送信
      - gpt-4o-mini の JSON Mode を利用し、レスポンスをバリデーションして ±1.0 にクリップ
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
      - API 失敗時は該当チャンクをスキップ（フェイルセーフ）、部分成功時は既存スコアを保護するため書き換え対象コードのみ DELETE→INSERT
      - JSON mode の前後余分テキスト対策（最外の {} を抽出してパース）
    - calc_news_window(target_date) ユーティリティを提供（UTC naive datetime を返す）
    - _validate_and_extract 等の堅牢なレスポンス検証ロジックを実装

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド回避）
      - マクロニュースは news_nlp の calc_news_window を利用して抽出、記事がある場合にのみ OpenAI を呼出
      - OpenAI 呼出しは専用の _call_openai_api 実装を用いる（モジュール間結合を避ける）
      - API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）
      - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）

- データ基盤（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを提供
    - market_calendar 未登録時は曜日（土日）ベースのフォールバックを使用
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック付き）
    - 最大探索範囲で無限ループ防止（_MAX_SEARCH_DAYS）
  - ETL パイプライン (pipeline)
    - ETLResult dataclass を導入（取得・保存件数、品質問題、エラー等を集約）
    - 差分更新・バックフィルの方針を実装するためのユーティリティ関数（テーブル存在チェック、最大日付取得等）
  - etl パッケージは pipeline.ETLResult を再エクスポート

- リサーチ（kabusys.research）
  - ファクター計算 (research.factor_research)
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離を計算（不足時は None）
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER / ROE を算出
    - DuckDB を用いた SQL + ウィンドウ関数中心の実装（外部 API にはアクセスしない）
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）をバッチで取得
    - calc_ic(factors, forwards, factor_col, return_col): スピアマンのランク相関（IC）を実装
    - rank, factor_summary: ランク付けと統計サマリー（外部ライブラリ依存なし）

### Changed
- （初回リリースのため該当なし）

### Fixed
- ニュース / レジーム系のロバストネス強化
  - LLM レスポンスの JSON パース失敗や不正データに対してログを残してフォールバック（0.0 かスキップ）する挙動を明示
  - DuckDB の executemany に空リストを渡さない安全処理（DuckDB 0.10 の制約を考慮）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キー周りは明示的に要求し、未設定時は ValueError を送出（安全マージン）
- OS 環境変数は自動 .env 上書きから保護（protected set を利用）

---

注記（設計方針の繰り返し）
- すべての時刻処理やウィンドウはルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を内部で参照しない等）
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT など）
- 外部 API 呼び出し（OpenAI / J-Quants）はフェイルセーフに設計し、部分失敗が全体を停止させない方針

今後の予定（例）
- モデルやプロンプトのチューニング、追加メトリクスの導入
- 発注・実行（execution）モジュールの統合テスト強化
- テストヘルパーや CI 環境向けの設定の整備

以上。