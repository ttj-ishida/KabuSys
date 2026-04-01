CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。本プロジェクトは「Keep a Changelog」仕様に準拠しています。

v0.1.0 - 2026-04-01
-------------------

概要
  初回公開リリース。本パッケージは日本株のデータパイプライン、ファクター研究、AIベースのニュースセンチメント判定、およびマーケットカレンダー管理を中心としたライブラリ群を提供します。設計全般において「ルックアヘッドバイアス排除」「フェイルセーフ」「DuckDB を用いたローカル分析」を重視しています。

Added
  - パッケージ基本情報
    - パッケージ名: kabusys、バージョン 0.1.0 (src/kabusys/__init__.py)
    - パブリックサブパッケージを __all__ で公開: data, strategy, execution, monitoring（後続実装想定）

  - 環境設定モジュール (src/kabusys/config.py)
    - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）
    - エクスポート形式（export KEY=val）やシングル/ダブルクォート、コメント付き行の堅牢なパース実装
    - OS 環境変数を保護する protected 上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - Settings クラスでアプリケーション設定をプロパティ経由で提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境判定等）
    - 入力検証（KABUSYS_ENV, LOG_LEVEL 等）と必須環境変数の _require による明示的エラー

  - AI モジュール (src/kabusys/ai/)
    - ニュース NLP (src/kabusys/ai/news_nlp.py)
      - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini、JSON mode）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）
      - バッチング（最大 20 銘柄/コール）、記事数/文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）
      - レスポンス検証ロジック（JSON 辞書抽出、results リスト/各要素検証、スコア ±1.0 クリップ）
      - フェイルセーフ設計: API 失敗時は該当チャンクをスキップし、既存データを不必要に消さない（部分書込保護）
      - テスト容易性のため OpenAI 呼び出しは差し替え可能（ユニットテストで patch 対応）

    - レジーム判定 (src/kabusys/ai/regime_detector.py)
      - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に日次で書き込み
      - マクロニュース抽出用キーワード群、LLM モデル gpt-4o-mini、リトライ/バックオフ、API 失敗時のデフォルト macro_sentiment=0.0（フェイルセーフ）
      - レジームスコアの閾値（bull/neutral/bear）判定、DB へ冪等的な BEGIN/DELETE/INSERT/COMMIT 書込みとロールバック処理

  - データモジュール (src/kabusys/data/)
    - カレンダー管理 (src/kabusys/data/calendar_management.py)
      - JPX マーケットカレンダーの夜間差分更新フロー（calendar_update_job）と market_calendar テーブル管理
      - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - DB データ優先の挙動、未登録日は曜日ベースのフォールバック、最大探索日数による安全制限、バックフィル/整合性チェック

    - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
      - ETLResult データクラスの導入（ETL 実行結果の構造化：取得/保存レコード数、品質問題、エラー一覧等）
      - 差分取得・バックフィル方針、品質チェック連携（quality モジュールへの委譲）、id_token 等の注入でテスト容易性確保
      - etl パッケージから ETLResult を再エクスポート

  - リサーチ / ファクター計算 (src/kabusys/research/)
    - factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出（DuckDB SQL ウィンドウ関数利用）、データ不足時の None 取り扱い
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比の算出（NULL の伝播を明示的に扱う）
      - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS 不正時は None）
      - DuckDB のみ参照する設計（実取引 API へはアクセスしない）

    - feature_exploration.py
      - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターン取得（LEAD を利用）
      - calc_ic: スピアマンランク相関（ランクは同順位の平均ランクを採用）、有効レコードが 3 未満なら None を返す
      - rank, factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）算出、外部ライブラリに依存しない実装

  - 共通技術的特徴
    - DuckDB を主たる分析 DB として利用
    - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等性とデータ保護
    - ロギングと警告による失敗時の可観測性向上
    - ルックアヘッドバイアス回避の明示的設計（date の扱いに注意、datetime.today() 参照を避ける）

Changed
  - なし（初回リリース）

Deprecated
  - なし（初回リリース）

Removed
  - なし（初回リリース）

Fixed
  - なし（初回リリース）

Security
  - なし（初回リリース）

Notes / 今後の予定（コードからの推測）
  - monitoring / execution / strategy サブパッケージは API 表示のみ。将来的に実行/発注/監視ロジックを実装予定と推測される。
  - jquants_client, quality モジュールは data 配下で使用されるが、実装詳細は本差分に含まれていない（外部 API ラッパー・品質検査ロジックとして統合予定）。
  - テスト用に OpenAI 呼び出しをモックできる設計になっており、ユニットテストが容易に作成可能。

お問い合わせ・補足
  - 実装の詳細や API 仕様、DB スキーマなどについて追加の変更履歴が必要であれば、該当モジュールの実装や使用例を元に更に詳細に分割して記載します。