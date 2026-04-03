# Changelog

すべての重要な変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式で記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報を公開（kabusys.__init__）。バージョン: 0.1.0。
  - モジュール群を整理して公開: data, strategy, execution, monitoring。

- 設定 / 環境読み込み (src/kabusys/config.py)
  - .env/.env.local と OS 環境変数からの自動設定読み込み機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト等で利用）。
    - .env の読み取りはクォート・エスケープ・インラインコメントなどを丁寧にパース。
    - OS 環境変数は保護（protected）され、上書き抑止が可能。
  - Settings クラスを実装し、アプリの設定値をプロパティ経由で取得可能に。
    - J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 実行モード 等のプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値は ValueError）。
    - is_live / is_paper / is_dev の便宜プロパティを追加。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - ニュースセンチメント分析 (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
    - バッチサイズ、記事数・文字数上限、トリムロジックを実装（トークン肥大化対策）。
    - リトライ戦略（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の型チェック、既知コードのみ採用）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するための差分 DELETE→INSERT ロジックを採用（DuckDB executemany の互換性を考慮し空リストチェックあり）。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - 日次で ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime を計算・保存。
    - マクロニュースはニュースタイトルをキーワードで抽出し、OpenAI に JSON 出力を要求して macro_sentiment を取得。
    - API 呼び出しはリトライ（指数バックオフ）・5xx の扱い・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため、target_date 未満のみを参照。datetime.today()/date.today() を直接参照しない設計。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - OpenAI クライアント呼び出しはモジュール間でプライベート関数を共有せず独立実装（テスト／結合性考慮）。
    - しきい値（bull/bear/neutral）と定数（モデル名、重み、リトライ回数等）を定義。

- リサーチ機能 (src/kabusys/research/)
  - ファクター計算 (research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足の場合は None を返す。
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損の際は None）。
    - 全て DuckDB SQL ベースで実装。prices_daily / raw_financials のみ参照し、本番発注 API 等へはアクセスしない方針。
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて計算。horizons の入力検証あり。
    - calc_ic: factor_records と forward_records を code で結合し、スピアマン順位相関（IC）を計算。十分なデータがない場合は None。
    - rank: 同順位は平均ランクにするランク付け関数（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median 等の統計サマリーを計算。
  - research パッケージの公開 API を整備（主要関数を __all__ でエクスポート）。

- データプラットフォーム (src/kabusys/data/)
  - マーケットカレンダー管理 (data.calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日）でフォールバックする実装。
    - next/prev では DB 登録日を優先し、未登録日は曜日フォールバックで一貫した結果を返す。探索上限（日数）を設定して無限ループを回避。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（未来日付の異常検出）を実装。
    - DuckDB からの日付変換ユーティリティやテーブル存在チェック等を提供。
  - ETL パイプライン (data.pipeline、data.etl)
    - ETLResult データクラスを実装し、ETL の実行結果（取得数・保存数・品質問題・エラー等）を格納・出力可能に。
    - パイプライン設計方針に従い、差分更新・idempotent 保存（jquants_client 経由）・品質チェック（quality モジュール）・バックフィル等を想定して実装。
    - data.etl は ETLResult を再エクスポート。

### 変更 (Changed)
- 設計上の注意点（ドキュメント・コード内コメントとして明示）
  - ルックアヘッドバイアス防止: 多くの処理で datetime.today()/date.today() を直接参照しない実装方針を採用。
  - DuckDB 互換性: executemany に空リストを渡せないバージョン(例: 0.10)を考慮した防御的実装を追加（空チェック）。

### 修正 (Fixed)
- 初期リリースのため特定のバグ修正履歴は該当なし（今後のリリースで追記）。

### セキュリティ (Security)
- OpenAI API キーは引数での注入または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を投げて明示的に通知。
- .env ファイル読み込み時に読み取り失敗が発生した場合は warnings.warn で通知し処理継続（致命的クラッシュを避ける）。

### 既知の制限 / 注意事項
- news_nlp / regime_detector は OpenAI を呼び出す設計のため、API 料金・レート制限に注意。
- DuckDB のバージョンによって SQL のバインディングの振る舞いが異なるため、executemany 周りの挙動に注意。
- calendar_update_job 等は外部 API（J-Quants）との依存があるため、API の可用性によっては取得が失敗し 0 レコードになることがある。
- 一部の関数はテスト容易性を考慮して内部 API 呼び出しを差し替え可能（unittest.mock.patch によるモック化を想定）。

---

今後の予定の例（例示）
- 0.2.0: 発注 / 実行モジュールの実装（kabu ステーション経由の実注文ロジック）、strategy モジュールの実装強化、性能チューニング。
- 0.1.x: バグ修正、テストケース拡充、OpenAI 呼び出し回数削減のためのキャッシュや要約ロジックの追加。

（以上）