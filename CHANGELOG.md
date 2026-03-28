Changelog
=========

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

[Unreleased]
------------

- 

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初回リリース (kabusys v0.1.0)
  - パブリックパッケージ初期化を追加（src/kabusys/__init__.py）。
    - __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を定義。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース機能を強化：コメント、export 文、シングル/ダブルクォートおよびバックスラッシュエスケープを正しく処理。
  - OS 環境変数を保護する protected 機能、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを実装し、J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル等の取得・バリデーションを提供。
    - 有効な KABUSYS_ENV 値: development / paper_trading / live
    - 有効な LOG_LEVEL 値: DEBUG / INFO / WARNING / ERROR / CRITICAL

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄別に記事をまとめて OpenAI（gpt-4o-mini）に投げるバッチ処理を実装。
    - 出力の検証、数値変換、±1.0 クリップ、部分失敗時の DB 書き換え保護（該当コードのみ置換）を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の UTC 変換）を提供（calc_news_window）。
    - レート制限・ネットワーク・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - テスト容易性のための _call_openai_api の差し替えポイントを用意。
    - score_news(conn, target_date, api_key=None) を公開し、ai_scores テーブルへ書き込み。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定を実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）、JSON パース堅牢化、リトライ/フォールバックの実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - score_regime(conn, target_date, api_key=None) を公開。

- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）の夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - DB の登録値優先、未登録日は曜日ベースでフォールバックする一貫した設計。探索上限や健全性チェックを実装。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装し ETL の結果（各種取得/保存数、品質問題、エラー）を構造化。
    - pipeline モジュールでの差分取得・保存・品質チェックの設計に沿ったユーティリティ関数・内部関数を実装（テーブル存在チェック、最大日付取得等）。
    - etl モジュールで ETLResult を再エクスポート。

  - jquants_client などの外部データクライアントは参照（実装は別モジュール想定）。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 約1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が0または欠損時は None）。
    - DuckDB SQL とウィンドウ関数を活用し営業日ベースの窓計算を実装。データ不足時は None を返す挙動。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）に対する将来リターンを一括で取得。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を実装（有効レコードが3未満なら None）。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー実装。
    - 研究ユーティリティは外部ライブラリに依存せず標準ライブラリ + DuckDB を使用。

- パッケージのエクスポート整理
  - research/__init__.py, ai/__init__.py 等で主要関数を __all__ により公開（例: score_news, calc_momentum 等）。

Changed
- 初版のため「Changed」は特になし。

Fixed
- 初版のため「Fixed」は特になし。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - 全てのモジュール（AI・研究・ETL 等）で datetime.today() / date.today() を内部判定に直接使用しない設計。すべて target_date ベースで計算。
  - prices_daily 等の SQL クエリは target_date 未満／以前といった排他条件を適切に使い、ルックアヘッドを防止。

- フェイルセーフ挙動:
  - 外部 API（OpenAI / J-Quants 等）失敗時は可能な限りフォールバック（0.0 やスキップ）して処理継続する設計。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、部分失敗時に既存データを不必要に消さない工夫を実装。

- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api）を差し替え可能にし、ユニットテストでのモックが容易。

- DuckDB 互換性:
  - executemany の空リスト回避、list 型バインドの回避など、DuckDB バージョン差分に配慮した実装。

Security
- 特記事項なし（現段階では機密情報は環境変数経由で取得する想定）。

Authors
- 初回実装（コードベースから推測して生成）。

翻訳・表現上の注:
- 本 CHANGELOG は提示されたコード内容から機能・設計を推測して作成したものであり、実際の外部モジュール実装（jquants_client 等）や運用方針に依存する部分については別途文書を参照してください。