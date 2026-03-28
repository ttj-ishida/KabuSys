# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に対応します。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージの初期リリース "KabuSys"（日本株自動売買システムのライブラリ基盤）。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"。

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
  - 保護されたキー（OS 環境変数）を上書きしない仕組みを実装。
  - Settings クラスを提供し、主要設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL 検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム、JSON mode を用いた厳格なレスポンス検証。
    - 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンス検証・スコアの ±1.0 クリップ。部分成功時に既存スコアを保護するため、対象コードのみ DELETE → INSERT。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - raw_news からマクロキーワードで抽出したタイトルを LLM（gpt-4o-mini）で評価。
    - マクロ評価は retry/backoff を実装し、API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。
    - レジームスコアの計算・クリップ・ラベル決定・market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に _call_openai_api を置き換え可能に設計。

- データ関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル、健全性チェックを実装。
  - ETL パイプライン（パブリックインターフェース）:
    - kabusys.data.pipeline に ETLResult データクラスを導入（kabusys.data.etl で再エクスポート）。
    - ETLResult: 各種取得数・保存数、品質チェック結果、エラー一覧、has_errors / has_quality_errors / to_dict を提供。
    - pipeline 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - 設計上、差分更新・バックフィル・品質チェックは Fail-Fast とせず呼び出し元へ状況伝達する方針。

- 研究・リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL伝播制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPSが0/欠損なら None）。
    - DuckDB ベースの SQL 実装により外部リソースに依存しない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンをまとめて取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計要約。
  - research パッケージの __all__ で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から提供）。

- DuckDB 互換性・運用上の配慮
  - DuckDB 0.10 における executemany の空リストバインド制約を考慮した実装（空チェックを導入）。
  - 日付はすべて datetime.date オブジェクトで扱い、timezone の混入を防止。

- ロギングと設計方針
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today() / date.today() の直接参照を避ける設計（関数引数で日付を注入）。
  - API 呼び出し失敗時はフェイルセーフ（例: マクロスコア 0.0、スコアリング処理のスキップ）で継続。
  - 多くの内部関数をテストで差し替え可能（patchable）に設計。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意:
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のプロダクト要件やドキュメントとは差異がある場合があります。
- 各モジュールは内部仕様（例: OpenAI API モデル指定、定数、閾値、ウィンドウ定義など）を含みます。運用時は環境変数設定や API キー管理、DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）の準備が必要です。