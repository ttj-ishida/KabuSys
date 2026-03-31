CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコアモジュールを追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py にパッケージ情報とエクスポート定義を追加（__version__ = 0.1.0）。
  - 設定管理:
    - src/kabusys/config.py
      - .env/.env.local と環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応した .env パーサを実装。
      - OS 環境変数上書きを防ぐ protected 機構、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を提供。
      - 各種設定プロパティを実装（J-Quants、kabuステーション、Slack、DBパス、環境判定、ログレベルなど）。不正値時に明示的な ValueError を送出。
  - AI 関連:
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を OpenAI（gpt-4o-mini）でバッチ処理し、銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む機能を実装。
      - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、記事集約、最大記事・文字数トリム、チャンクバッチ処理（_BATCH_SIZE=20）を実装。
      - API リトライ（429・接続断・タイムアウト・5xx）と指数バックオフ、レスポンスバリデーション、スコアクリップ（±1.0）、部分書込みによる部分失敗耐性を実装。
      - テスト容易性のため _call_openai_api をパッチ可能に実装。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
      - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみ使用）、API フェイルセーフ（失敗時 macro_sentiment=0.0）、OpenAI 呼び出しの独立実装等を含む。
  - データ基盤:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダーの夜間更新ジョブ(calendar_update_job)、営業日判定(is_trading_day)、前後の営業日探索(next_trading_day/prev_trading_day)、期間内営業日取得(get_trading_days)、SQ 判定(is_sq_day) を実装。
      - market_calendar が未取得の際の曜日ベースフォールバック、最大探索日数制限、バックフィル／健全性チェックを実装。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETL パイプライン基盤を実装。差分取得、保存（J-Quants クライアント経由で冪等保存）、品質チェックフレームワークの統合を想定。
      - ETLResult データクラスを導入し、etl モジュールから ETLResult を再エクスポート。
  - リサーチ（研究）機能:
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対ATR、出来高指標）、Value（PER、ROE）の計算関数を実装。DuckDB 上で完結する設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン算出(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、値のランク化(rank)、ファクター統計サマリー(factor_summary) を実装。外部依存を持たない純標準ライブラリ実装。
    - src/kabusys/research/__init__.py に主要関数を再エクスポート。
  - データユーティリティ:
    - src/kabusys/data/__init__.py（空のパッケージエントリ）
    - calendar/jquants_client への連携を想定（カレンダー取得・保存呼び出し）。
  - その他ユーティリティ/設計上の注意点（ドキュメントコメントとして実装に組込）
    - 多くの処理で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡すことでルックアヘッドバイアスを防止。
    - DuckDB の executemany の制約（空リスト不可）に配慮した実装。
    - OpenAI 呼び出しに関する詳細なリトライ方針とログ出力を実装。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし（実装段階でフェイルセーフや入力検証を多く導入）。

Security
- 環境変数取り扱いにおいて OS 環境（既存のプロセス環境変数）保護のため protected キー集合を導入し、.env による上書きを制御可能にした点を明記。

Notes / 開発者向けメモ
- OpenAI API の利用:
  - デフォルトモデルは gpt-4o-mini を使用。API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要がある（未設定時は ValueError を送出）。
  - テスト容易性のため、ニュース/レジームモジュールの内部 _call_openai_api を unittest.mock.patch で差し替え可能。
- データベース:
  - DuckDB を想定した SQL を採用。テーブル名やカラムの存在チェックを行うユーティリティを用意。
  - デフォルトの DB パスは設定で指定可能（DUCKDB_PATH / SQLITE_PATH）。
- ロギング:
  - 主要処理で情報・警告・例外ログを出すように実装。API リトライやパース失敗時に詳細ログを残す。

今後の予定（例）
- ETL の具体的なジョブスケジューリングと監査ログ出力の実装。
- 発注／実行関連モジュール（execution）、モニタリング（monitoring）、データ取得クライアント（jquants_client）の詳細実装と統合テスト。
- パフォーマンス最適化・大規模データ向けのクエリチューニング。
- ドキュメントと使用例（README, StrategyModel.md, DataPlatform.md 等）の充実。

---