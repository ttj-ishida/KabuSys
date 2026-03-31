Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」に準拠した形式を採用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（次のリリースに向けた変更をここに記載してください）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期公開
  - src/kabusys/__init__.py
    - パッケージ名とバージョン定義 (__version__ = "0.1.0")。
    - パブリックAPIとして data, strategy, execution, monitoring をエクスポート。

- 環境・設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - エスケープ・クォート・インラインコメントに配慮した堅牢な .env パーサー。
    - OS 環境変数を保護する protected 上書き制御。
    - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
    - 設定値のバリデーション（env 値と log level の許容値チェック、未設定での ValueError）。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信し、センチメント（ai_scores）を生成・保存。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
    - チャンク処理（最大 20 銘柄／リクエスト）、1銘柄あたりの記事数／文字数上限、レスポンスのバリデーションとスコアの ±1.0 クリッピング。
    - 429/ネットワーク断/タイムアウト/5xx を対象とした指数的バックオフによるリトライ。
    - DuckDB への冪等的書き込み（DELETE → INSERT）および部分失敗時の保護（書き込みコードを絞る）。
    - テスト容易性のため OpenAI 呼び出し部分（_call_openai_api）を差し替え可能に設計。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily / raw_news / market_regime を参照し、計算後に market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ設計。
    - OpenAI 呼出しは独立実装でモジュール間の結合を低減。
    - リトライ・バックオフ・エラー種別別ハンドリングを実装。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理：market_calendar テーブルの利用、曜日ベースのフォールバック、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（バックフィルと健全性チェックあり）。
    - DB がまばらな場合でも一貫した判定ができるよう DB 値優先・未登録は曜日フォールバックの方針。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプライン用ユーティリティと ETLResult（結果データクラス）の実装。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携想定）を想定した設計。
    - DuckDB 上の最大日付取得やテーブル存在チェックなどの内部ユーティリティ。

  - src/kabusys/data/__init__.py
    - データ関連パッケージの土台（クライアント参照等のためのモジュール構成）。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター計算（モメンタム、ボラティリティ、バリュー）を提供:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）。
      - calc_volatility: 20日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio。
      - calc_value: per / roe（raw_financials と prices_daily を併用）。
    - DuckDB SQL を用いた実装で外部 API には依存しない。
    - データ不足時の None 扱いとログ出力。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、リード関数利用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）実装（ties の平均ランク処理）。
    - rank: 値→ランク変換（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。

- 研究用パブリック API
  - src/kabusys/research/__init__.py
    - 主要関数群（calc_momentum 等）とデータの正規化ユーティリティを再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数パーサーの堅牢化（クォート内部のバックスラッシュエスケープ処理、export プレフィックス対応、コメント検出ルール改良）。
- DuckDB 実装上の注意点対応（executemany に空リストを渡せないバージョンへの互換処理）。

Security
- OpenAI / 外部 API キーは明示的に渡すか環境変数 OPENAI_API_KEY を設定する必要がある点を明記。未設定時は ValueError を送出して失敗早期検知。

Design Notes / その他重要点
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定など、全ての処理で datetime.today() / date.today() を参照せず、caller が target_date を渡す設計。
  - DB クエリは target_date 未満／以前などの排他条件を明示して将来データ使用を防止。
- DB 書き込みは原則冪等（DELETE→INSERT や ON CONFLICT を想定）で実装。例外時は ROLLBACK を明示的に試行し、ROLLBACK 失敗はログ出力して上位へ伝播。
- OpenAI 呼び出し箇所はテストで差し替え可能（_call_openai_api を patch することでユニットテストの安定化を容易に）。
- DuckDB を想定した SQL 実装で、互換性やバージョン特性（配列バインドの不安定さ等）に配慮した実装。

Known issues
- 一部モジュール（例: jquants_client の実装）は外部依存として参照されており、実行には該当クライアント実装が必要。
- strategy / execution / monitoring パッケージは __all__ で公開されているが、このリリースでの実装は最小限（未提供の関数や拡張は今後のリリースで追加予定）。

License
- （該当情報をここに記載してください）

--- 
（以上）