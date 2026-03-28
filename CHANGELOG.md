CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

注記
----
- 日付はリリース日として現在の日付 (2026-03-28) を使用しています（ソースコードの __version__ は 0.1.0）。
- 内容は提示されたコードベースの実装から推測して記載しています。

Unreleased
----------
- 未リリースの変更はありません。

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py により version と公開モジュールを定義。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱い。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定をプロパティで取得可能。
  - 環境変数保護（既存 OS 環境変数の保護）を考慮した上書きロジックを実装。

- AI / ニュースNLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None):
    - raw_news と news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini）でバッチ（最大 20 銘柄）センチメント評価。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - JSON mode のレスポンスを厳密にバリデートし、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - DuckDB への冪等書き込み（DELETE→INSERT）で部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - calc_news_window(target_date) ユーティリティ（JST 窓を UTC naive datetime に変換）。

- AI / レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None):
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次判定。
    - ma200_ratio の算出（ルックアヘッド防止のため target_date 未満データのみを利用）。
    - マクロニュースは news_nlp.calc_news_window を用いて期間を算出し、最大 N 件を抽出して LLM に渡す。
    - LLM 呼び出しはリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を採用。
    - 結果を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - テスト容易性のため _call_openai_api は独立実装で patch 可能。

- 研究（Research）モジュール（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算（不足時は None）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から直近財務データを取得し PER/ROE を計算。
    - DuckDB を用いた SQL 中心実装（外部 API 非依存）。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンを算出（複数ホライズン一括クエリ）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - rank(values): 平均ランク処理（タイの扱いは平均ランク）。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリーを返す。
  - research パッケージで主要関数を再エクスポート。

- データ基盤（src/kabusys/data/）
  - calendar_management.py:
    - market_calendar を利用した営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合の曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants クライアント経由でカレンダー差分を取得し冪等保存、バックフィル・健全性チェックを実装。
    - 探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止。
  - pipeline.py / etl.py:
    - ETLResult データクラス（ターゲット日・取得/保存済みレコード数・品質問題リスト・エラーリスト等）を提供。
    - ETL の差分取得方針、バックフィル、品質チェックの設計方針を反映したユーティリティ群。
    - DuckDB の制約（executemany の空リスト不可等）を考慮した実装。
  - jquants_client 用フックを想定した抽象化（jq.fetch_market_calendar / jq.save_market_calendar 等の呼び出し）。

- 汎用/互換性
  - DuckDB 日付/値の取り扱いヘルパー（_to_date 等）を多数のモジュールで整備。
  - ロギングと警告（失敗時に例外を投げずフォールバック）を積極採用し、フェイルセーフを重視。
  - テストしやすさを意識した設計（外部 API 呼び出し箇所を patch 可能にする等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）
- 実装上では以下の互換性・堅牢化対応を含む:
  - .env パースの厳格化（クォート内エスケープ、コメント判定、export プレフィックス）。
  - OpenAI レスポンスの JSON パースで前後ノイズを吸収する保険処理（最初と最後の {} を抽出して解析）。
  - API エラー種別に応じた再試行/非再試行の振る舞いを明確化。

Security
- OpenAI API キーが未設定の場合は明示的に ValueError を発生させる（AI 系関数）。
- .env 自動ロードはプロジェクトルート探索に依存し、誤ったカレントディレクトリ依存を避ける設計。
- OS 環境変数を保護するため .env 上書き時に protected set を用いる。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 今後の注意点（推奨）
- OpenAI（gpt-4o-mini）呼び出しには課金・レート制限が関わるため、本番環境では API キー管理と呼び出し頻度に注意してください。
- DuckDB のバージョン差分（特に executemany の動作）に依存したワークアラウンドを実装しているため、DuckDB のバージョンアップ時は互換性テストを推奨します。
- CSV/外部データ取り込みや jquants_client の具体的実装（fetch/save 実装）は別途実装が必要です（このリリースはクライアントフックを想定した設計）。

Authors
- ソースコードの docstring と実装に基づき自動推測して作成。

Acknowledgements
- 本リリースはシステム設計（データ取得・ETL・研究・AI 評価・実行分離）とテスト可能性を念頭に置いて構成されています。