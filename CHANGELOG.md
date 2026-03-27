CHANGELOG
=========

すべての注目すべき変更履歴はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
既知の互換性や設計方針、フェイルセーフ挙動についても併記しています。

[Unreleased]
------------

（現時点のコードベースから推測すると初回リリース相当の実装が含まれるため、以下は最初の公開バージョン向けの履歴です。）

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys/__init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - ファイル読み込み時には既存 OS 環境変数を protected として上書きを制御。
  - .env パーサを実装:
    - 空行・コメント行・export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープと対応する閉じクォートの検出。
    - クォートなしの場合のインラインコメント判定（# の直前が空白/タブのときのみコメントと扱う）。
  - Settings クラスを提供しアプリケーション設定をプロパティで取得:
    - J-Quants, kabuステーション API, Slack, データベースパス (duckdb/sqlite)、システム環境（KABUSYS_ENV, LOG_LEVEL）の既定値とバリデーションを実装。
    - KABUSYS_ENV / LOG_LEVEL の不正値は ValueError を送出。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - チャンク処理（最大20銘柄/回）、1銘柄あたり記事数上限・文字数トリムを実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx を対象にエクスポネンシャルバックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - API 応答の厳密な検証ロジックを実装（JSON 抽出、"results" の存在確認、コード整合性、スコア数値化、スコアの ±1.0 クリップ）。
    - 書き込みは冪等操作（対象コードのみ DELETE → INSERT）で実行。DuckDB の executemany の制約を考慮。
    - テスト容易性のため _call_openai_api を内部で分離しモック差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経連動）200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily から target_date 未満のデータのみを用いることでルックアヘッドバイアスを回避。
    - マクロ記事が存在する場合のみ LLM を呼び出し、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - OpenAI 呼び出しでのリトライ/バックオフ、JSON パース失敗でのフォールバックを実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。
    - テスト差し替え用に _call_openai_api を分離。
- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - データ未取得日は曜日ベース（平日を営業日）でフォールバックする一貫性のある設計。
    - next/prev_trading_day は探索上限（_MAX_SEARCH_DAYS）を設定して無限ループを防止。
    - calendar_update_job により J-Quants から差分取得→冪等保存（バックフィル・健全性チェック含む）。
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを提供し、ETL の各指標（取得数・保存数・品質問題・エラー）を集約して返却・ロギング可能に。
    - 差分更新、backfill、品質チェック（quality モジュール）を想定した ETL 設計。
    - DuckDB に対するテーブル存在チェック、最大日付取得などのユーティリティ実装。
    - jquants_client と連携するためのフック（fetch/save）を想定。
- リサーチ用途モジュール (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、ma200 乖離）, Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）, Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時の None 扱い、結果は (date, code) をキーとした dict リストで返却。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）, calc_ic（Spearman ランク相関で IC を算出）, rank（同順位は平均ランク）, factor_summary（count/mean/std/min/max/median）を実装。
  - zscore_normalize を data.stats から再エクスポート。
- テスト性・運用性強化
  - 多くの外部呼び出し（OpenAI API 呼び出し）を内部関数で分離し unittest.mock.patch 等で差し替え可能にしてユニットテストを容易化。
  - 各モジュールで詳細なログ出力（情報・警告・デバッグ）を追加し運用時のトラブルシューティングを支援。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キーは関数引数で明示的に注入可能（api_key 引数があり None の場合のみ環境変数 OPENAI_API_KEY を参照） — テスト時や運用でのキー管理を容易化し、暗黙的なグローバル依存を軽減。

Notes / 設計上の重要事項
- ルックアヘッドバイアス対策:
  - 全ての AI / リサーチ処理で内部的に datetime.today() / date.today() を直接参照しない設計（外部から target_date を与える方式）。
  - DB クエリでは target_date 未満や範囲制約を明確にして将来データを参照しないようにしている。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを 0.0（中立）にフォールバックする等、致命的障害にならないように設計。
- DuckDB 互換性:
  - executemany の空リスト制約や日付型取り扱いなど、DuckDB 特性に配慮した実装（空パラメータチェック、date 変換ユーティリティ等）。
- IDempotency:
  - データ書き込みは可能な限り冪等操作（DELETE → INSERT、ON CONFLICT 想定）で設計し、部分失敗時のデータ保護を重視。

開発者向けメモ
- 自動 .env ロードを無効にしたいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI の API 呼び出しをユニットテストで差し替える場合は各モジュールの _call_openai_api をモックしてください（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- DuckDB 接続は各関数に注入して使用します。実行環境での DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）が前提です。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（現在はパッケージ出口を用意）。
- ai モデル選択やプロンプト最適化のさらなる改善。
- 品質チェック（quality モジュール）の詳細ルール拡張とアラート連携（Slack 等）。

-----------------------------------------------------------------------------
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット単位の履歴とは差異がある可能性があります。必要であればコミットログやリポジトリ履歴に基づく正確な履歴化を行います。）