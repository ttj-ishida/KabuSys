# CHANGELOG

すべての重要な変更履歴をここに記録します。フォーマットは Keep a Changelog に準拠しています。  
（初期リリース: バージョンはパッケージの __version__ に合わせて 0.1.0）

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース。日本株自動売買 / データ基盤 / リサーチ用のコアモジュールを実装。
  - kabusys.__init__
    - パッケージ公開 API を定義（data, strategy, execution, monitoring）。
  - kabusys.config
    - .env ファイルおよび環境変数からの設定読み込みを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等のプロパティとバリデーションを実装。
  - kabusys.ai.news_nlp
    - ニュース記事を銘柄別に集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント（ai_score）を計算して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、記事トリミング（記事数・文字数制限）、チャンク（最大 20 銘柄）でのバッチ送信をサポート。
    - レスポンスの厳密なバリデーション、数値変換、スコア ±1.0 のクリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ、API 失敗時は該当チャンクをスキップするフェイルセーフ実装。
  - kabusys.ai.regime_detector
    - ETF（1321）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - OpenAI 呼び出しは独立実装、API失敗時は macro_sentiment=0.0 で継続するフェイルセーフ、リトライロジックとログ出力を実装。
    - DuckDB に対する冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 値がない場合の曜日ベースのフォールバック、最大探索日数制限、NULL 値の扱い（警告ログ）などを設計。
    - 夜間バッチ更新 job（calendar_update_job）を実装し J-Quants クライアント経由で差分取得・保存（バックフィル・健全性チェック含む）。
  - kabusys.data.pipeline / kabusys.data.etl
    - ETL パイプラインの基礎（差分取得、バックフィル、品質チェックの呼び出し、idempotent 保存）を実装。
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー情報を格納、辞書化対応）。
  - kabusys.research
    - ファクター計算・特徴量探索モジュールを実装。外部依存を持たない純 Python + DuckDB 実装。
    - 提供関数:
      - factor_research.calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。
      - factor_research.calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
      - factor_research.calc_value: raw_financials に基づく PER / ROE の計算（EPS が 0/欠損時は None）。
      - feature_exploration.calc_forward_returns: 将来リターンの一括取得（任意ホライズンをサポート）。
      - feature_exploration.calc_ic: スピアマンランク相関（IC）計算（欠損・少数レコードは None を返す）。
      - feature_exploration.factor_summary / rank: 統計サマリー・ランク関数を実装。
    - zscore_normalize を kabusys.data.stats から再エクスポート。
  - 実装方針全体
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() の直接参照を避け、全ての関数は target_date を受け取る設計。
    - DuckDB を主要なデータストアとして想定し、互換性を考慮した実装（executemany の空リスト回避等）。
    - OpenAI 呼び出し部分はテスト容易性のため差し替え可能（内部 _call_openai_api をモック可能）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （該当なし）

## 注意事項 / 補足
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は ValueError を送出します。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定し、レスポンスパース失敗や API エラー発生時はフェイルセーフ動作（スコア 0.0 またはチャンクスキップ）を行い、システム全体の停止を防ぎます。
- .env 自動ロードはプロジェクトルート検出が成功した場合にのみ実行され、OS 環境変数は保護されます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョン差異（list バインドや executemany の挙動）を考慮した実装になっていますが、運用環境での動作確認を推奨します。

---

今後のリリースでは以下を想定しています:
- strategy / execution / monitoring 各モジュールの実装強化とテストカバレッジ追加
- API クライアント（kabuステーション / J-Quants）の詳細実装と認証フロー整備
- モデル評価・学習パイプラインの追加
- より詳細な品質チェック機能の追加

（必要であれば上記の今後予定を CHANGELOG の次回エントリに移行します）