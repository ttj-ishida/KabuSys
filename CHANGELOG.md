# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-03-27

初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開モジュール: data, research, ai, （strategy / execution / monitoring を __all__ に含む設計）

- 環境設定
  - 環境変数 / .env 管理モジュール（src/kabusys/config.py）
    - プロジェクトルートを __file__ 起点で探索（.git または pyproject.toml）して .env/.env.local を自動読み込み
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env のパース機能強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）
    - OS 環境変数を保護する protected 機構（.env.local での上書き時も考慮）
    - Settings クラスを提供（必須環境変数を _require で検証）
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック
      - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値
      - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション
      - is_live / is_paper / is_dev のヘルパー

- AI（自然言語処理 / 市場レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - calc_news_window: JSTベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30）
    - score_news: raw_news / news_symbols を集約し OpenAI (gpt-4o-mini) に JSON Mode で問い合わせ、銘柄ごとのセンチメント（ai_scores テーブルへ書込）
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム（最大記事数・最大文字数）でトークン肥大化対策
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）で指数バックオフ
    - レスポンスバリデーション（JSON パース、results 型、code の整合性、スコア数値検査）
    - スコアは ±1.0 にクリップ
    - DuckDB 0.10 の executemany 空リスト制約を考慮した実装（空リスト時は executemany を呼ばない）
    - テスト容易性のため _call_openai_api をモンキーパッチ可能に設計

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を算出
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）
    - マクロキーワードで raw_news をフィルタし、OpenAI により macro_sentiment を評価
    - API 呼び出しはリトライ戦略を実装、失敗時は macro_sentiment = 0.0 として続行（フェイルセーフ）
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト用に _call_openai_api を差し替え可能

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン関連（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラー一覧などを集約）
    - 差分更新・バックフィル等の設計方針を実装に反映するヘルパー関数（テーブル存在チェック、最大日付取得等）
    - jquants_client / quality と連携する想定（save/fetch の呼び出し経路を確保）

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（平日のみ）でフォールバック
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェック（将来日付の異常検出）を実装

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を DuckDB SQL で計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等を計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を算出
    - 全関数は prices_daily / raw_financials のみ参照し、本番売買 API にはアクセスしない設計
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを取得
    - calc_ic: スピアマン（ランク）による IC 計算（rank ユーティリティを内部提供）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
    - 外部ライブラリに依存せず標準ライブラリのみで実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に必要（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を発生させて早期検出。

## 注意事項 / 設計上の留意点
- ルックアヘッドバイアス対策:
  - 主要なスコアリング処理（news_nlp, regime_detector, research.*）は内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計。
  - prices_daily や raw_news のクエリは target_date 未満 / 半開区間などルックアヘッドを避ける条件になっている。
- フェイルセーフ:
  - OpenAI API の一時エラーや解析失敗時は例外を上位へ投げずにスコアをスキップ／0.0 フォールバックするケースが多く、ETL/バッチ処理の継続性を重視。
- DuckDB 互換性:
  - DuckDB 0.10 の executemany における空リスト制約への対応（空パラメータ時に呼び出さない）を行っている。
- テスト性:
  - OpenAI 呼び出し部はモジュール内で private 関数化されており、unittest.mock.patch による差し替えを想定している。
- ロギング:
  - 各モジュールは詳細な logger 出力を行い、失敗やフォールバック理由をログに残す。

## 今後の予定（TODO / 予定機能）
- monitoring モジュール等、運用監視系の実装（__all__ に含まれているが本リリースでは詳細実装が含まれていない部分あり）
- strategy / execution 層の具体的な注文発行ロジック（kabuステーション連携や取引シミュレーションの拡充）
- jquants_client / quality モジュールの追加・拡張（ETL の実稼働連携強化）
- ドキュメント（使用例、スキーマ定義、運用手順等）の拡充

---

この CHANGELOG はコードベース（ソース内の docstring / コメント / 実装）から推測して作成しています。実際のリリースノートとして利用する場合は、差分やパブリック API 変更点を確認の上、必要に応じて加筆・修正してください。