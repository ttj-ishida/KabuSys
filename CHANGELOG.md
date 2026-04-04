# CHANGELOG

すべての変更は「Keep a Changelog」(https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

注: この CHANGELOG は与えられたコードベースから推測して作成しています。実装の意図・設計方針や公開 API の要点を中心にまとめています。

## [Unreleased]

- （現在のスナップショットに対する未リリース変更はありません）

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システム「KabuSys」の基盤機能群を実装・公開。

### 追加 (Added)

- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリックエクスポート: data, strategy, execution, monitoring（パッケージ公開インターフェースに含める）

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルートは .git 又は pyproject.toml を基準に探索（CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）
  - .env パーサ実装:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートあり/なしの差異を考慮）
  - Settings クラスを提供し、プロパティ経由で設定値を取得
    - J-Quants / kabuステーション / LINE / DBパス / 監視関連 / システム設定等のプロパティ
    - 必須環境変数未設定時のエラー（_require）
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）
    - 各種パスは Path オブジェクトで返す（expanduser 対応）
    - kill flag, CPU/Memory/Disk threshold 等の監視閾値を環境変数化

- AI 関連: ニュース NLP と市場レジーム判定 (kabusys.ai)
  - ニュースセンチメント集計と書き込み (kabusys.ai.news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとのテキストを生成
    - タイムウィンドウ定義: target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（calc_news_window を提供）
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、最大 _BATCH_SIZE（20）銘柄ずつバッチ処理
    - 1銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - レスポンスの厳格バリデーションとスコア ±1.0 にクリップ
    - 書き込みは冪等: DELETE（date, code）→ INSERT をトランザクションで実行（部分失敗時に他銘柄を保護）
    - リトライポリシー: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ
    - テストしやすさ: _call_openai_api をモック可能に設計
    - API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用
    - ログ出力で処理状況を記録（対象記事数・チャンク数・書込み銘柄数等）

  - マーケットレジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321（日本225連動）について 200 日移動平均乖離を計算（_calc_ma200_ratio）
      - ルックアヘッドを防ぐため target_date 未満のデータのみ使用
      - データ不足時は中立（1.0）でフォールバックし WARN ログ
    - マクロ経済ニュースを抽出（マクロキーワード群でタイトルを検索）
    - OpenAI によるマクロセンチメント評価（gpt-4o-mini、JSON 出力）を取得（max 記事数制限）
    - レジームスコア合成: 重み付け（MA 70%、マクロ30%）、スコアを -1..1 にクリップ
    - ラベル付与: bull / neutral / bear の閾値判定
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ挙動
    - モジュール結合を避ける設計（news_nlp の内部 helper を共有しない）

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算
      - データ不足時は None を返す設計
      - DuckDB のウィンドウ関数を利用した SQL ベース実装
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算
      - true_range の NULL 伝搬を考慮した堅牢な実装
    - calc_value: raw_financials の最新財務データと prices_daily を組合せて PER/ROE を算出
      - target_date 以前の最新財務レコードを取得するロジックを実装
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括算出
      - horizons のバリデーション（正整数かつ <= 252）
    - calc_ic: スピアマンランク（Information Coefficient）を計算。データ不足（<3）で None を返却
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能
    - rank: 同順位を平均ランクで処理するランク変換関数
  - zscore_normalize を kabusys.data.stats から再エクスポート（research パッケージ API の一部）

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したアルゴリズム
    - カレンダー夜間更新ジョブ (calendar_update_job): J-Quants から差分取得・冪等保存（バックフィル/健全性チェック含む）
    - 最大探索日数やバックフィル日数等の安全策を実装（無限ループや異常日付を回避）
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult dataclass を導入し、ETL 実行結果・品質チェック・エラーを集約して返す
    - 差分更新、バックフィル、品質チェックの骨子を実装（jquants_client および quality モジュールと連携）
    - ETLResult.to_dict() で品質問題を辞書化して監査ログに利用可能
    - _table_exists / _get_max_date 等の内部ユーティリティを実装
    - kabusys.data.etl で ETLResult を再エクスポート

- 実装品質・テスト支援
  - OpenAI 呼び出し部をモック可能にし、エラー処理やリトライ挙動のテストを容易化
  - DuckDB 互換性考慮（executemany の空リスト回避や配列バインド不安定性への対策）
  - ルックアヘッドバイアス回避方針: datetime.today()/date.today() を計算内部で直接参照しない設計を採用（target_date に依存する）

### 変更 (Changed)

- 初回公開のため該当なし（新規実装）

### 修正 (Fixed)

- 初回公開のため該当なし

### 廃止 (Deprecated)

- 初回公開のため該当なし

### 削除 (Removed)

- 初回公開のため該当なし

### セキュリティ (Security)

- 環境変数から API キー等を読み込む設計
  - .env の自動読み込みはデフォルト有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - OS 環境変数は保護（protected set）され、.env の上書きから除外される仕組みを導入

---

補足（設計上の注記）
- 多くのモジュールで「フェイルセーフ」方針を採用しており、外部 API の一時的失敗時は例外でプロセス全体を停止させず、部分結果を保持したり中立値（例: 0.0 や 1.0）へフォールバックする実装が見られます。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 方針記載等）、部分失敗が他データを巻き込まない配慮がされています。
- DuckDB を一次 DB と想定した SQL+Python の設計であり、外部発注や資金移動に関わる処理はこのスナップショットには含まれていません（strategy/execution/monitoring は公開 API に含まれているが実装ファイルはスナップショットに含まれない可能性あり）。

もし CHANGELOG に特定の粒度（例: モジュール毎の変更履歴、将来のリリース計画、既知の制限・TODO など）を追加したい場合は、その要望を教えてください。必要に応じて追記・細分化します。