KEEP A CHANGELOG
すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" のフォーマットに従います。
<https://keepachangelog.com/ja/1.0.0/>

保持方針: 初期リリースの内容は以下の通りです。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-29
-------------------
Added
- 初回リリース: kabusys パッケージの初期実装を追加。
  - パッケージ情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py:
    - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（.env, .env.local の優先順）。
    - プロジェクトルート探索: .git または pyproject.toml を基準に自動検出（カレントワーキングディレクトリに依存しない）。
    - .env 行パーサ: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラス: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等のプロパティを提供。KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev ヘルパを実装。
- AI（ニュースNLP / レジーム検出）:
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄単位に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出・ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）の算出（calc_news_window）。
    - バッチサイズ、記事数・文字数のトリム、JSON Mode 応答のバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等的な書き込み（DELETE→INSERT）。
    - API 失敗（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライし、最終的にフェイルセーフ（スキップ）で継続。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を unittest.mock.patch で置換可）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロ記事抽出はキーワードマッチ（日本・米国のマクロ語彙）で行い、最大記事数を制限。
    - OpenAI 呼び出しのリトライ戦略、API失敗時のフォールバック（macro_sentiment=0.0）、レスポンスパース失敗時の安全処理を実装。
    - ルックアヘッドバイアス防止の設計（datetime.today() を参照しない、DB クエリは target_date 未満のデータのみ使用）。
- データプラットフォーム（ETL / カレンダー / パイプライン）:
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの基本骨格を実装。差分取得、保存（jquants_client 経由の冪等保存）、品質チェックの取り扱い方針を定義。
    - ETLResult データクラスを実装（取得数／保存数／品質問題／エラー一覧を保持）。to_dict により品質問題をシリアライズ可能。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理機能を実装（market_calendar テーブル参照）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days 等の営業日判定ユーティリティを提供。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar の冪等更新（バックフィル・健全性チェック含む）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）で動作。
- リサーチ（ファクター計算・特徴量探索）:
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対ATR、流動性指標）、Value（PER/ROE）を計算。データ不足時の None 処理。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず組み込みロジックで実装。
  - src/kabusys/research/__init__.py:
    - 上記関数群を公開。
- その他:
  - DuckDB を主要なローカル分析ストアとして統合しているコード例（各モジュールで DuckDB 接続を受ける設計）。
  - ロギングと詳細なデバッグ情報を各関数で出力（logger あり）。
  - テスト容易性を意識した設計（OpenAI 呼び出しの差し替え、環境ロード無効化フラグ等）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- API キー（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）は環境変数から取得する設計。運用時は適切にシークレット管理（環境変数管理・Vault 等）を行ってください。
- OpenAI 呼び出しは外部 API であるためレート制限や課金に注意が必要です。

Notes / 実装上の設計方針（重要）
- ルックアヘッドバイアス回避: AI モジュールは内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える方式を採用。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT、ON CONFLICT 相当の扱い）。
- OpenAI API 呼び出しは JSON Mode を使用し、レスポンスを厳密に検証。復元処理や前後テキスト混入への対処を含む。
- API エラーは再試行（指数バックオフ）を行い、再試行後も失敗する場合はフェイルセーフ（スキップ／デフォルト値）で継続する設計。

既知の制約 / TODO（今後の改善候補）
- strategy / execution / monitoring サブパッケージはパッケージ公開対象に含まれているが、今回提示されたソースにはそれらの実装が含まれていない（将来的な実装予定）。
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value に注記あり）。
- DuckDB の executemany に関する互換性注意（空リスト不可）へのワークアラウンド実装があるが、将来的により洗練された API 層にまとめる余地あり。
- 単体テスト・統合テストの実装は別途整備が必要（OpenAI / J-Quants クライアントはモック差し替えでテスト可能な設計）。

（以上）