Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Semantic Versioning を採用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
-------------------

Added
- 基本パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、公開サブパッケージ指定（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py:
    - .env / .env.local から自動的に環境変数を読み込む機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応。
    - 既存 OS 環境変数を保護するため protected キーを扱い、.env.local は既定で上書きする挙動。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルのプロパティを実装。未設定時の明確なエラーメッセージや値検証を実施。
    - デフォルトのデータベースパス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を定義。
- AI モジュール（OpenAI と連携する自動スコアリング）:
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約し、gpt-4o-mini（JSON mode）でセンチメント評価を行い ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの最大記事数（10）と最大文字数（3000）でプロンプト肥大化を抑制。
    - API 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx を対象）を行い、レスポンス検証・数値変換・±1.0 クリップを実施。
    - DuckDB の executemany に対する互換性（空リスト回避）を考慮した安全な DB 書き込み（DELETE → INSERT）を実装。
    - テスト容易化のため _call_openai_api を patch で差し替え可能。
  - src/kabusys/ai/regime_detector.py:
    - 日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースの LLM センチメント（重み 30%）を合成。
    - OpenAI API 呼び出しはリトライ/バックオフを実施し、API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を担保。エラー時は ROLLBACK を試行。
    - 内部での DuckDB クエリはルックアヘッドバイアス防止（target_date 未満のデータのみ使用）を意識して実装。
- データプラットフォーム関連:
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダーの管理・夜間バッチ更新（calendar_update_job）および営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得のときは曜日ベース（平日＝営業日）にフォールバックする堅牢な設計。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETL パイプラインの骨組みを実装（差分取得、保存、品質チェックの呼び出し方針）。
    - ETLResult dataclass を定義し、実行結果（取得件数、保存件数、品質問題、エラー）を構造化して返す API を追加。
    - 内部ユーティリティでテーブル存在チェックや最大日付取得を実装。
  - src/kabusys/data/__init__.py と etl の再エクスポートにより外部から ETLResult を利用可能に。
  - jquants_client など外部クライアントは data パッケージ内から参照する設計（fetch/save の抽象化）。
- リサーチ/ファクター関連:
  - src/kabusys/research/factor_research.py:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER・ROE）等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。すべて DuckDB の prices_daily / raw_financials テーブルのみ参照。
    - 計算結果は (date, code) をキーにした辞書リストで返す仕様。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ + duckdb で実装。欠損や短いサンプルへの安全処理あり。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- その他ユーティリティ:
  - テストフレンドリな設計（OpenAI 呼び出しの差し替えポイント、DuckDB の互換性配慮など）を各所で採用。
  - ロギングを多用し、失敗時やフォールバック時に詳細情報を残す実装。

Changed
- 初期リリースのため「変更」はなし（初回導入分に該当）。

Fixed
- 初期リリースのため「修正」はなし（実装時点の意図的なフェイルセーフ・検証ロジックを含む）。

Security
- 環境変数の自動読み込みで OS 環境変数を上書きしない保護機構（protected キー）を導入。
- OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数で指定する必要があり、未設定時は ValueError を送出することで誤動作を防止。

Notes / Migration / Requirements
- 必須環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY は ai.score_news / ai.score_regime 実行時に必要（関数引数での上書きも可能）。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI は gpt-4o-mini（JSON mode）を前提とする設計。API 仕様変更やモデル差し替え時は _call_openai_api の差し替え・修正が必要。
- DuckDB のバージョン差異（executemany の空リスト処理など）を考慮した互換性処理を含むため、古いバージョンでも動作を想定しているが、推奨環境は DuckDB の比較的新しい安定版を推奨。

既知の制限
- news_nlp / regime_detector は外部 OpenAI API に依存しており、API 呼び出しの失敗はスコアにフェイルセーフ値（0.0）を割り当てるが、品質保証のため API キー管理や利用制限に注意が必要。
- 一部処理は DuckDB の SQL ウィンドウ関数に依存（ROW_NUMBER, LAG, LEAD 等）。極端に古い DuckDB 環境では互換性問題が発生する可能性あり。

Authors
- コードベースの内容から推測して生成（CHANGELOG は実装内容を元に自動生成）。

-----