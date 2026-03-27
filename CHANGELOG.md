Keep a Changelog
=================

すべての重要な変更点はこのファイルに記載します。  
このプロジェクトは「Keep a Changelog」の方針に準拠しています。

[Unreleased]

v0.1.0 - 2026-03-27
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
- パッケージ公開情報:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める。
- 設定・環境変数管理機能:
  - src/kabusys/config.py を追加。
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用）。
  - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント規則を考慮）。
  - override と protected を使った環境変数上書き制御（OS 環境変数保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル判定等のプロパティを簡単に取得可能に。
  - 必須環境変数未設定時は ValueError を送出する挙動を統一。

- AI（自然言語処理）機能:
  - src/kabusys/ai/news_nlp.py を追加:
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - JST 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ送信（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数制限、JSON Mode 応答の検証、スコアの ±1.0 クリップ、部分失敗に耐える DB 更新（該当コードのみ DELETE→INSERT）を実装。
    - API リトライ（429/ネットワーク断/タイムアウト/5xx）、レスポンスの堅牢なパースとバリデーションを実装。
    - OpenAI API キー未設定時は ValueError を送出。
  - src/kabusys/ai/regime_detector.py を追加:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出、LLM（gpt-4o-mini）呼び出し（JSON応答）と再試行戦略、API失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成・閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー未設定時は ValueError を送出。

- データプラットフォーム（Data）関連:
  - src/kabusys/data/calendar_management.py を追加:
    - market_calendar を使った営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録有無に応じた曜日ベースのフォールバック、最大探索日数制約、カレンダー夜間バッチ更新（calendar_update_job）を実装。
    - J-Quants クライアント連携による差分取得と冪等保存の仕組み。
  - src/kabusys/data/pipeline.py を追加:
    - ETLResult dataclass を定義し、ETL の取得数・保存数・品質問題・エラーを集約。
    - 差分更新ロジック、バックフィル戦略、品質チェックとの連携を想定したユーティリティ関数を提供（テーブル存在確認・最大日付取得等）。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- リサーチ（Research）機能:
  - src/kabusys/research/factor_research.py を追加:
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 処理、ログ出力、SQL ベースの実装により外部 API への依存なし。
  - src/kabusys/research/feature_exploration.py を追加:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンのランク相関）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize は data.stats から提供されるユーティリティを再利用）。

- 内部ユーティリティ/設計上の配慮:
  - 各モジュールで datetime.today() / date.today() を直接参照しない設計（全て target_date を引数で受ける）によりルックアヘッドバイアスを排除。
  - DuckDB に対する互換性・制約（executemany の空リスト不可 等）を考慮した実装。
  - OpenAI 呼び出し部分はテスト時に差し替え可能（モジュール内の _call_openai_api を patch できるように設計）。
  - 各種処理で失敗時はフェイルセーフに振る（例: API 失敗時は 0.0 を返す、例外は局所的に処理してログに記録し上位で再送出する場合がある）。

Changed
- 該当なし（初回公開のため変更履歴は無し）。

Fixed
- 該当なし（初回公開のため修正履歴は無し）。

Security
- 環境変数読み込みで OS 環境変数を保護する protected 機構を導入（.env が意図せず重要な環境変数を上書きしないように配慮）。
- OpenAI API キーの未設定を明確に検出し ValueError を送出することで誤った無認証呼び出しを防止。

Notes / 開発者向け注意事項
- OpenAI 呼び出しは gpt-4o-mini を前提に JSON Mode（response_format）で行っているため、API 仕様変更時は各モジュール内の _call_openai_api 実装を確認すること。
- news_nlp / regime_detector ともにレスポンスのパースや検証を厳格化しているが、実際の運用では LLM の出力多様性に注意し、必要に応じてプロンプトや検証ロジックの調整が必要。
- DuckDB のバージョン差異によるバインド挙動や日付型の扱いに配慮した実装があるため、運用環境の DuckDB バージョンに注意すること。
- calendar_update_job は外部 API（J-Quants）に依存するため、API エラー時は 0 を返す安全な動作をするようになっている。

今後の予定（提案）
- ファクター群の追加（PBR・配当利回り等）及びファクターブレンドの自動検証機能の追加。
- AI モジュールのテストやモック用ユーティリティの整備（プロンプトのユニットテスト含む）。
- ETL の並列化・進捗監視機能、監視用メトリクスの追加。