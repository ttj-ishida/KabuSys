# Changelog

すべての重要な変更点をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。

現在の最新バージョンは 0.1.0 です。

[Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージを導入。バージョン情報を __version__ = "0.1.0" として公開。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に指定。

- 設定 / 環境管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env 行パーサーを実装。export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 必須環境変数取得用の _require と、設定のバリデーション（KABUSYS_ENV, LOG_LEVEL など）を実装。
  - Slack、kabuステーション API、データベースパス、監視閾値（CPU/MEM/DISK）、PID ファイルパス等のプロパティを提供。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込む score_news を実装。
    - JST のニュース時間ウィンドウ計算（calc_news_window）を実装（前日 15:00 JST 〜 当日 08:30 JST の範囲を UTC に変換して扱う）。
    - バッチ処理（最大 20 銘柄/API 呼び出し）、銘柄ごとの記事集約、文字数トリム、チャンクごとのリトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - OpenAI レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 型チェック、スコア ±1 にクリップ）を実装。
    - API 呼び出しをテストで差し替えやすいように _call_openai_api を分離。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily, raw_news, market_regime テーブルを用いる。ma200 計算、マクロ記事抽出、OpenAI コール、スコア合成、冪等（BEGIN / DELETE / INSERT / COMMIT）での DB 書き込みを実装。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ、リトライ/バックオフ、5xx の挙動区別など堅牢性を考慮。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX 市場カレンダー管理ロジックを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した判定、探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止を実装。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存処理）。

  - ETL パイプライン (pipeline, etl, etl の公開)
    - ETLResult データクラスを導入（取得・保存件数、品質チェック結果、エラーリスト等を格納）。
    - 差分更新、バックフィル、品質チェック連携を行うパイプライン設計に沿ったユーティリティを準備。
    - jquants_client 経由での取得・保存処理を想定したインターフェースを整備。

- 研究用ユーティリティ (kabusys.research)
  - factor_research: モメンタム、バリュー、ボラティリティ（ATR/流動性等）を計算する calc_momentum / calc_value / calc_volatility を実装。prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターン計算 calc_forward_returns、IC 計算 calc_ic、ファクター統計 factor_summary、ランク変換 rank を実装。
  - data.stats の zscore_normalize を再エクスポート。研究ワークフローで必要となる基本的計算を提供。
  - 全関数はルックアヘッドバイアス防止のため datetime.today() を参照しない設計。

### 仕様上の注意（実装上の重要ポイント）
- ルックアヘッド対策
  - AI / 研究系処理は内部で date / target_date ベースで動作し、datetime.today()/date.today() を参照しないことでルックアヘッドバイアスを排除。
  - DB のクエリも target_date より前のデータのみを参照するように設計。

- フェイルセーフ / 冗長性
  - OpenAI 呼び出しでのレート制限・ネットワーク障害や 5xx を考慮したリトライ実装（指数バックオフ）、最終的に安全なデフォルト（例: macro_sentiment=0.0）で処理継続。
  - DB 書き込みはトランザクションで冪等・ロールバック処理を行い、ROLLBACK の失敗時は警告ログを出力。

- テストを考慮した設計
  - OpenAI 呼び出し部はモジュールごとに _call_openai_api を分離しており、ユニットテスト時に差し替え（patch）しやすい。

### 既知の制約 / 未実装
- PBR・配当利回り等一部バリューファクターは未実装（calc_value に注記あり）。
- ETL pipeline の完全実装（差分取得ロジックの上位実行関数等）や jquants_client の詳細は外部モジュールに依存。
- DuckDB バインドの互換性に関して注意書き（executemany に空リストを渡さない等）をコード内に記載。

### セキュリティ
- 特記事項なし。

---

貢献や不具合報告、改善提案は issue / PR で歓迎します。