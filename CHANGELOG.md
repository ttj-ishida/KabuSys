CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------

- Known issues / TODO
  - data.pipeline._get_max_date 関数末尾に誤記載（"return date.fro" のような未完のコード）があり、実行時に例外が発生する可能性があります。次リリースで修正予定。
  - 一部外部クライアント（jquants_client など）のエラー伝播・例外ハンドリングやエッジケースの追加テストを強化予定。
  - monitoring モジュール（__all__に含まれるが、今回のコード断片では実体が見当たらない）について実装／公開を検討中。

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py によりパッケージ公開（data, strategy, execution, monitoring をエクスポート対象に指定）。
- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - export KEY=val 形式・クォート処理・行コメント処理などを考慮した .env パーサ実装。
    - OS 環境変数を保護する protected 上書きガード、KABUSYS_DISABLE_AUTO_ENV_LOAD フラグによる自動ロード無効化。
    - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / ログレベル / 環境判定ユーティリティ等のプロパティ）。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。
- AI / NLP 機能
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - レスポンスの厳格なバリデーション（JSON復元ロジック、results 配列検査、コード照合、数値チェック）、スコアを ±1.0 にクリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT の形で対象コードのみ置換）を実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - calc_news_window: JST を基準にしたニュース集計ウィンドウ計算ユーティリティ（UTC naive datetime を返す）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio 計算、マクロキーワードでの記事抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出、スコア合成・閾値判定。
    - API失敗時は macro_sentiment=0.0 とするフェイルセーフ、DBへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ガード）。
    - OpenAI 呼び出しの再試行／5xx 判別ロジックを実装。
- Data / ETL / カレンダー機能
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを含む ETL パイプライン基盤（差分取得、バックフィル、品質チェック集約の設計方針を反映）。
    - jquants_client からのデータ取得・保存と quality チェックの統合インターフェース（実装は jquants_client / quality に依存）。
    - ETL 実行結果の辞書化 to_dict（quality_issues をシリアライズ）。
  - src/kabusys/data/etl.py
    - ETLResult の公開再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブルの夜間差分更新用 calendar_update_job）。
    - 営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - market_calendar が未取得時の曜日ベースフォールバック、DB 値優先の一貫したロジックと最大探索日数制限、健全性チェック（未来日付の閾値）とバックフィル戦略。
    - jquants_client 連携による取得・保存呼び出し箇所を用意。
- Research / ファクター計算 / 統計
  - src/kabusys/research/
    - factor_research.py
      - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR等）、Value（PER, ROE）等の計算関数を実装。
      - DuckDB を用いた SQL ベース実装で、ファクターは (date, code) ベースの dict リストとして返却。
      - データ不足時の None ハンドリングやログ出力を実装。
    - feature_exploration.py
      - 将来リターン算出（任意ホライズン、デフォルト [1,5,21]）、IC（Spearmanランク相関）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - research パッケージ __init__ で主要関数をエクスポート。
- テストしやすさ / 設計上の配慮（全体）
  - ルックアヘッドバイアス防止のため、date.today()/datetime.today() を直接参照しない設計（API 呼び出しは target_date 引数で明示）。
  - OpenAI 呼び出しをラップしてテスト時に差し替え可能な設計（_call_openai_api の patch）。
  - DuckDB 書き込みは冪等性を意識（既存行の削除→挿入や ON CONFLICT の指向）。
  - API エラーやパース失敗はフェイルセーフでスコアを 0.0 にフォールバック、または該当チャンクをスキップして全体処理を継続。
  - ログ出力により処理状態やエラーの追跡が容易に設計。

Security
- 環境変数の読み込み時に OS 環境変数を保護する protected セットを採用（.env が OS 環境を上書きしないデフォルト動作）。
- 必須の機密情報（OpenAI API key, Slack token, kabu API password, J-Quants token 等）は Settings が _require により未設定時に明示的にエラーを出す設計。

Notes / Compatibility
- 外部依存: openai SDK（OpenAI クライアントの chat.completions.create を利用想定）、duckdb。
- news_nlp と regime_detector は gpt-4o-mini の JSON Mode を利用する想定でプロンプト/レスポンスパースロジックを組み込んでいるため、OpenAI API のレスポンス仕様変更に弱い箇所がある（将来の SDK/API 変更に注意）。
- DuckDB の executemany の仕様差異（空リスト不可）を回避するガードを含む。

Acknowledgements
- 初期設計は DataPlatform / StrategyModel 等のドキュメントセクションに沿って実装（コメントで参照あり）。
- ユニットテストを想定したフック（API 呼び出しの差し替えポイント、設定読み込みの無効化フラグ等）を多数用意。

----- 

将来的なリリースでは、既知の不具合修正（_get_max_date の修正、monitoring モジュールの実装など）、追加の監視・運用ツール、より詳細な品質チェックルールやテストの拡充を予定しています。