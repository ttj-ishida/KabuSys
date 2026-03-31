# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買システムのコアライブラリを公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージ識別子とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開モジュール一覧を __all__ で定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を protected として上書き保護。
  - .env パースの堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の細かな取り扱い。
  - 必須設定取得用の _require の実装（未設定時に ValueError）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / Slack / DBパス / 監視設定 / env/log_level 判定など）。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の限定値）。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) の JSON mode で一括スコアリング。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄当たり記事数・文字上限でトリム。
    - 429・接続断・タイムアウト・5xx を対象に指数バックオフでリトライ、その他はスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score の検証、スコアの ±1.0 クリップ）。
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（部分失敗時に既存スコアを保護）。
    - calc_news_window: JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換するユーティリティ。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントはマクロキーワードで絞った raw_news タイトルを OpenAI に投げて JSON で取得。
    - 設計上の注意点: ルックアヘッドバイアス回避（date 引数ベース、today の参照を排除）、API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - LLM 呼び出しは内部で独立実装、retry ロジック・例外ハンドリングを実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (data.pipeline)
    - ETLResult dataclass を定義し、取得数・保存数・品質問題・エラー情報を集約。
    - 差分更新・バックフィル・品質チェック方針の実装方針を反映した設計（実際の取得・保存は jquants_client を使用する想定）。
  - ETL 公開インターフェース (data.etl)
    - ETLResult を再エクスポート。
  - マーケットカレンダー管理 (data.calendar_management)
    - market_calendar テーブルを利用した営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への保存（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル窓などの安全策を実装。

- リサーチ用ユーティリティ (kabusys.research)
  - ファクター計算 (research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を算出（EPS 0/欠損時は None）。
    - DuckDB に依存した SQL ベース実装で、外部 API 呼び出しなし。
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（営業日数）に基づく将来リターンを一括取得。horizons の入力検証あり。
    - calc_ic: Spearman（ランク）による Information Coefficient 計算。データ不足（<3）では None を返す。
    - rank: 同順位に対して平均ランクを割り当てるランク関数（丸めで ties の検出精度向上）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出する統計サマリー。

- その他
  - 複数モジュールで OpenAI API 呼び出しを行うが、テスト時に差し替え可能な内部 _call_openai_api を用意（unittest.mock.patch でのモックを想定）。
  - DuckDB を前提とした SQL 実行インターフェースを全面的に採用。

### 変更 (Changed)
- 初版のため「変更」はありません（最初の公開）。

### 修正 (Fixed)
- 初版のため「修正」はありません。

### 削除 (Removed)
- 該当なし。

### 既知の制限・注意事項 (Notes / Known limitations)
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定が必須。api_key 引数で注入可能。
- J-Quants / kabu ステーション / Slack 連携に必要な環境変数は Settings にて必須判定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
- DuckDB 用のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）が必要。ETL による事前ロードが前提。
- News / Regime の LLM 呼び出しは gpt-4o-mini の JSON mode を想定。API レスポンスの不確実性に対して堅牢化（パース失敗や未知コードの無視、フェイルセーフのデフォルト値）を行っている。
- 日付取り扱いはルックアヘッドバイアス防止のため関数引数ベース（date 引数）で実装。datetime.today()/date.today() の直接参照は最小限に留める方針。

---

今後のリリース案内（例）
- Unreleased: 追加 API、モニタリングと自動注文の実装、より詳細な品質チェックルールなどを予定。