# CHANGELOG

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

全てのバージョンはセマンティック バージョニングに従います。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ公開
  - パッケージ名: kabusys
  - パッケージバージョン: 0.1.0
  - トップレベル __all__ エクスポート: data, strategy, execution, monitoring

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装
    - プロジェクトルート判定: .git または pyproject.toml を親ディレクトリから探索して決定
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ: export 前置・クォート・エスケープ・インラインコメント等の取り扱いに対応
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を参照
  - システム設定検証
    - KABUSYS_ENV 値検証 (development, paper_trading, live)
    - LOG_LEVEL 値検証 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - デフォルトパス設定: DUCKDB_PATH / SQLITE_PATH

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み
    - 特徴
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window
      - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリムしてプロンプト肥大化を抑制
      - JSON Mode を利用した厳密なレスポンス検証（results 配列、code と score の検証）
      - 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他エラーはスキップ（フェイルセーフ）
      - スコアは ±1.0 にクリップ
      - DuckDB への挿入は冪等（DELETE → INSERT）で部分失敗時に既存スコアを保護
      - テスト容易化のため _call_openai_api はモック差し替え可能
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - フロー
      - ma200_ratio を DB（prices_daily）から計算（target_date 未満のデータのみ参照してルックアヘッドを防止）
      - raw_news からマクロキーワードでフィルタしたタイトルを取得
      - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON で評価
      - レジームスコア合成・クリップ・ラベル付け
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 特徴
      - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
      - OpenAI 呼び出しは専用実装でモジュール間の結合を避ける
      - テスト向けに _call_openai_api を差し替え可能

- Research（ファクター計算・特徴量探索）(kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率を計算
    - calc_value: PER・ROE を raw_financials と prices_daily から計算（PBR/配当未実装）
    - 設計: DuckDB の SQL を活用し、prices_daily / raw_financials のみ参照。結果は (date, code) キーの辞書リストで返却
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算
    - rank: 同順位は平均ランクにするランク関数
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を計算
    - 設計: 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで実装

- Data（データプラットフォーム）(kabusys.data)
  - calendar_management
    - JPX カレンダー管理ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB に market_calendar がない場合は曜日ベースのフォールバック（週末は非営業日）
    - next/prev/get_trading_days は DB の登録値を優先し、未登録日は曜日フォールバックで一貫した挙動
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックあり）
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを導入（target_date, fetched/saved カウント、品質チェック結果、エラー一覧）
    - 差分更新・バックフィル・品質チェック方針を反映
    - 内部ユーティリティ: テーブル存在確認・最大日付取得関数など
  - etl モジュールは ETLResult を再エクスポート

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 既知の制限 (Known limitations)
- calc_value: PBR・配当利回りは未実装（将来追加予定）
- DuckDB の executemany に空リストを渡せない制約を考慮して実装している（互換性目的）
- OpenAI レスポンスのパースは堅牢化済みだが、LLM の出力が大幅に期待と異なる場合はスキップして結果が欠落することがある
- 日時取り扱いはすべて date/UTC-naive datetime を使用し、ルックアヘッドバイアスを避ける設計

### テスト向けフック
- AI 呼び出しラッパ（_call_openai_api）はユニットテストで patch してモックに差し替え可能

---

今後の予定（例）
- PBR・配当利回りなどのバリューファクター追加
- strategy / execution / monitoring モジュールの実装・統合テスト
- ドキュメントの充実（Usage ガイド、デプロイ手順、運用監視）

以上。