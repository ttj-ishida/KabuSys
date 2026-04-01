CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。重大な後方互換性の破壊がある場合は明記します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-01
-------------------

Added
- パッケージ初版リリース (バージョン 0.1.0)
  - src/kabusys/__init__.py にて公開モジュールとバージョンを定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パーサを実装し、export 形式・クォート（シングル/ダブル）・エスケープやインラインコメントの扱いに対応。
    - OS 環境変数を保護する protected 機構（.env.local の上書き制御含む）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB /監視/システム関連設定をプロパティ経由で取得。必須変数未設定時は ValueError を送出。
    - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- ニュース NLP スコアリング（AI）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク単位（デフォルト20銘柄）でのバッチ処理、1銘柄あたり記事数上限・文字数トリム（デフォルト：最大10記事、3000文字）を実装。
    - JSON Mode を前提にレスポンスを厳密にバリデーションし、不正レスポンスに対する復元（最外の {} 抽出）や未知コードの無視を実装。
    - 429／接続断／タイムアウト／5xx に対する指数バックオフのリトライ実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - DuckDB 互換性考慮（executemany に空リストを渡さないガード）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み済み銘柄数を返す。

- レジーム判定（AI + MA）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA200 比率計算（ルックアヘッド防止のため target_date 未満データのみ使用）。
    - raw_news からマクロキーワードでフィルタしたタイトル抽出を実装。
    - OpenAI 呼び出しの独立実装とリトライ/フォールバック（API失敗時は macro_sentiment=0.0）。
    - レジーム結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値がある場合はそれを優先、未登録日は曜日（週末）ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得および冪等保存、バックフィル/健全性チェック（未来日 sanity チェック）を実装。
    - DB 未取得時のフォールバック動作を明確化。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスを実装し ETL の集計結果・品質問題・エラー情報を保持。to_dict で品質問題を辞書化可能に。
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックのインターフェースを整備（jquants_client, quality 連携想定）。
    - 内部ユーティリティで DuckDB テーブル存在チェックや最大日付取得の実装（DuckDB の取り扱い注意を含む）。

- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算関数を実装:
      - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を算出。
      - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
      - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を算出。
    - DuckDB 内の SQL ウィンドウ関数を用いた高効率実装。外部 API 呼び出しは行わない設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを一括で取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン ランク相関（IC）を計算。
    - rank(values): 同順位は平均ランクとするランク関数の実装（浮動小数点の丸め対策あり）。
    - factor_summary(records, columns): 各ファクター列の count/mean/std/min/max/median を算出。
    - すべて標準ライブラリと DuckDB のみで実装。

- パッケージ公開インターフェース
  - 各サブパッケージで主要関数を __all__ に定義して再エクスポート（例: kabusys.ai.score_news / regime_detector の公開）。

Changed
- 実装方針と設計上の注意点を明文化（各モジュール内 docstring に記載）。
  - すべての AI / データ処理で「ルックアヘッドバイアスを避ける」方針を徹底（datetime.today()/date.today() を処理内部で直接参照しない）。
  - OpenAI 呼び出しはテスト容易性のため関数差し替え可能（unittest.mock.patch でモック化を容易に）。

Fixed
- DuckDB の互換性対応:
  - executemany に空リストを渡さないチェックを追加（DuckDB 0.10 の制約対策）。

Notes / Design Decisions
- フェイルセーフの挙動:
  - LLM 呼び出しが失敗した場合は例外を投げずに中立スコア（0.0）で継続する箇所を多く設け、パイプライン全体の可用性を優先。
- トランザクション/冪等性:
  - DB 書き込みは冪等に行う（DELETE → INSERT のパターン、BEGIN/COMMIT/ROLLBACK 管理）。
- テストしやすさ:
  - OpenAI 呼び出しや環境ロードを外から制御/差し替えできる設計。

Security
- 本リリースでは外部依存（OpenAI・J-Quants・kabu API）の認証情報は Settings 経由で環境変数から取得する。必須トークン未設定時は明示的にエラーとなる（ValueError）。環境変数の取り扱いは .env の自動ロードを行うが、明示的に無効化可能。

今後の予定（示唆）
- ai モジュールのモデル/パラメータを設定化し外部から調整可能にする。
- ETL の詳細な品質チェックルール実装と監査ログ出力強化。
- テストカバレッジ拡充（特に OpenAI 呼び出し周りのモックテスト）。

--- 

注: 上記 CHANGELOG はリポジトリ内のソースコードと docstring から推測して作成した初期リリース記録です。必要があれば、より細かいコミット単位の情報（実際のコミットメッセージや日付）を組み込んで更新できます。