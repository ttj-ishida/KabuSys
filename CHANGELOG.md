CHANGELOG
=========
すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングに従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-03
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能群を追加。
  - パッケージ初期化
    - パッケージ名: kabusys、バージョン __version__ = "0.1.0"。
    - __all__ に data, strategy, execution, monitoring を公開（strategy 等の実装ファイルは別途存在を想定）。
  - 設定 / 環境変数管理 (kabusys.config)
    - .env と .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定等に対応した .env パーサ実装。
    - OS 環境変数を保護するため読み込み時に既存キーは上書きされない（ただし .env.local は override）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供。J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム環境（development/paper_trading/live）等のプロパティとバリデーションを実装。必須変数は _require で明示的にエラーを出す。
  - AI モジュール (kabusys.ai)
    - news_nlp
      - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込み。
      - タイムウィンドウは JST 前日 15:00 〜 当日 08:30 を UTC に変換して使用（calc_news_window）。
      - バッチ処理: 最大 20 銘柄／コール、1銘柄あたり最大 10 記事かつ 3000 文字にトリム。
      - レート制限 (429)、ネットワーク断、タイムアウト、5xx は指数バックオフでリトライ。その他のエラーはスキップしフェイルセーフで継続。
      - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code と score の整合性、数値検査）。スコアは ±1.0 でクリップ。
      - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
    - regime_detector
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime を日次判定（ラベル: bull/neutral/bear）。
      - マクロニュースはマクロキーワードでフィルタして最大 20 件を LLM に渡す。LLM 呼び出し失敗時は macro_sentiment = 0.0 として継続。
      - OpenAI 呼び出しは独立実装、再試行ロジックとログ出力を備える。
      - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）方式で行い、例外時は ROLLBACK を試行して上位へ伝播。
  - データ処理 / ETL / カレンダー (kabusys.data)
    - pipeline.ETLResult を公開（kabusys.data.etl 経由で再エクスポート）。
    - ETLResult: ETL 実行結果の dataclass（取得件数、保存件数、品質問題リスト、エラーリスト等）とユーティリティ（to_dict, has_errors, has_quality_errors）。
    - calendar_management
      - JPX マーケットカレンダーの読み書き・判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - market_calendar が未取得のときは曜日（平日のみ営業日）でフォールバック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を更新。lookahead デフォルト 90 日、バックフィル 7 日、健全性チェックを実装。
    - pipeline / ETL の設計方針に沿った差分更新、バックフィル、品質チェックの枠組み（quality モジュール連携を想定）。
  - リサーチ機能 (kabusys.research)
    - factor_research
      - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離を算出（data: prices_daily）。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。
      - calc_value: 最新の raw_financials を用いて PER (EPS が有効な場合) と ROE を算出。
      - 全関数は DuckDB 接続を受け取り SQL ベースで計算、結果は (date, code) をキーとする dict リストを返す。
    - feature_exploration
      - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを算出。horizons の検証あり。
      - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データが不足（有効レコード < 3）なら None を返す。
      - rank: 同順位は平均ランクを割り当てるランク関数（丸め処理で ties の検出漏れを防止）。
      - factor_summary: 指定カラムの count/mean/std/min/max/median を算出。
  - ロギングと堅牢性
    - 各モジュールで詳細なログ出力を実装（info/debug/warning）。
    - DB 書き込みはトランザクションで保護し rollback の失敗を警告。
    - いくつかの安全措置（API 失敗時のデフォルト値、入力バリデーション）を実装。
  - テスト支援
    - OpenAI 呼び出し箇所は patch で差し替え可能に実装しユニットテストを容易化。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱い:
  - 必須の機密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings のプロパティで明示的に要求し、未設定時は ValueError を投げる。
  - .env 読み込みは既存の OS 環境変数を上書きしない（保護）。必要なら .env.local で上書き可能。
  - 自動読み込みをテスト等で無効化するフラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

開発者向けノート
- すべての日付参照（スコアリングや ETL）で datetime.today()/date.today() を直接参照せず、明示的に target_date を受け取る設計にしてルックアヘッドバイアスを防止している点に留意してください。
- OpenAI API 呼び出しはモデル名やバッチサイズ、リトライ回数などの定数で調整可能（デフォルト: model=gpt-4o-mini, batch_size=20, max_retries=3）。
- DuckDB との executemany に空リストを渡すと動作が不安定なバージョンがあるため、空チェックを入れている点に注意してください。

お問い合わせ・貢献
- バグ報告や改善提案は issue を通じてお願いします。README / ドキュメントに実運用の注意事項（API キー管理、運用時の kill flag や PID 管理など）を追記予定です。