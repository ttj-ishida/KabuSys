Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- 特になし（初回リリースにて主要機能を実装）

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。
    - プロジェクトルートを .git / pyproject.toml から探索して .env / .env.local を読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val フォーマット、クォート・エスケープ、行末コメントなどに対応したパーサを実装。
    - .env 読込時に OS 環境変数を保護する仕組み（protected set）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能にした。
    - J-Quants / kabu ステーション / Slack / データベース（DuckDB、SQLite）設定など。
    - システム環境（KABUSYS_ENV）、ログレベル検証ロジック、is_live / is_paper / is_dev 判定を実装。
    - 必須環境変数未設定時は ValueError を送出する _require 関数を提供。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルからニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST、UTC変換対応）。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム（最大10記事・3000文字/銘柄）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコア ±1 にクリップ。
    - DuckDB への冪等的書き込み（取得済みコードのみ DELETE → INSERT）で部分失敗時の保護。
    - テスト容易性のため _call_openai_api を内部で分離（unittest.mock.patch で差替え可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事を取得、OpenAI 呼び出しで macro_sentiment を算出。
    - API リトライ・フォールバック（失敗時は 0.0）やレスポンスパース例外に対する安全化を実装。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時はロールバックを試行。
    - モジュール間の結合を抑えた設計（news_nlp の内部関数は利用せず専用の呼び出し実装）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX 市場カレンダーを管理するユーティリティ群を実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日（週末）ベースでフォールバック。
    - DB 登録値を優先し、未登録日は曜日ベースで補完する一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義し ETL 実行結果を集約（取得数、保存数、品質問題、エラー等）。
    - 差分取得、保存（jquants_client を利用した冪等保存）、品質チェック（quality モジュール）の流れを想定した設計。
    - backfill・calendar lookahead 等の設定と、DuckDB テーブル存在チェック等のユーティリティを実装。
    - etl パッケージ外から使いやすいように ETLResult を公開（kabusys.data.etl）。

- 研究・ファクターモジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）等を DuckDB ベースで計算。
    - データ不足時の扱い（十分な履歴がなければ None）を明示。
    - DuckDB 内でウィンドウ関数を用いた実装（営業日ベースの窓、スキャン範囲のバッファ）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意 horizon 対応）、IC（Spearman の ρ）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等外部ライブラリに依存しない純 Python / SQL 実装。
  - research パッケージ __all__ を整備して主要関数を再エクスポート。

- 汎用実装 / 設計方針
  - ルックアヘッドバイアス防止: 各処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - フェイルセーフ: 外部 API 失敗時は処理を継続（適切なデフォルトやスキップ）する実装方針。
  - DuckDB 互換性ワークアラウンド（executemany の空リスト対策など）を反映。
  - OpenAI 呼び出しについてはリトライ、タイムアウト、JSON Mode のレスポンス整形・検証を重視。

Changed
- 初回リリースのため対象外。

Fixed
- 初回リリースのため対象外。

Security
- 初回リリースのため対象外。

Notes / 既知事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給する必要がある（未設定時は ValueError を送出）。
- .env パーサは多くのシェル形式に対応しているが、極端に特殊なフォーマットは未対応の可能性がある。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が所定の列を持つことを前提としている。
- 実運用前に各種閾値（CPU/MEM/DISK 等の監視値、AI 閾値、チャンクサイズ等）の調整を推奨。

Contributing
- バグ報告・機能提案は issue を作成してください。Pull Request はテストを含めて送ってください。

License
- 明記なし（リポジトリの LICENSE を参照してください）。