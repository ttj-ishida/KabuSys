CHANGELOG
=========
すべての変更は Keep a Changelog の方針に準拠して記載しています。  
このファイルは、公開されているコードの内容から推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------
（現在のリポジトリに未リリースの変更はありません）

0.1.0 - YYYY-MM-DD
------------------
初回公開リリース。以下の主要機能と設計方針を実装しています。

Added
-----
- 全体
  - パッケージ初期化とエクスポートを追加 (src/kabusys/__init__.py)。
  - バージョン情報を "0.1.0" として定義。

- 環境設定
  - 環境変数/ .env 管理モジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索。
    - .env / .env.local の自動読み込み（優先順: OS環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト向け）。
    - export KEY=val やシングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いを含む堅牢なパーサ実装。
    - 必須設定取得用の Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベルなどのプロパティ）。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と is_live / is_paper / is_dev のユーティリティ。

- AI（ニュース NLP / レジーム検出）
  - ニュースセンチメントを銘柄別に付与するニュースNLPモジュールを追加 (src/kabusys/ai/news_nlp.py)。
    - 前日15:00 JST ～ 当日08:30 JST の記事ウィンドウを計算するユーティリティ calc_news_window。
    - raw_news と news_symbols を集約し、1銘柄当たり最大記事数・文字数でトリムして OpenAI にバッチ送信。
    - gpt-4o-mini を用いた JSON Mode 出力のパース・バリデーション、スコアの ±1.0 クリップ、部分成功時の DB 置換ロジック（DELETE → INSERT）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ、その他エラーはスキップしてフェイルセーフに継続する設計。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)。
    - 日次で ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio 計算、マクロキーワードによる raw_news フィルタ、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計。

- データ（Data Platform）
  - カレンダー管理モジュールを追加 (src/kabusys/data/calendar_management.py)。
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日リスト取得・SQ日判定。
    - market_calendar が未取得のときは曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - J-Quants API からの差分取得と夜間バッチ更新（calendar_update_job）、バックフィルや健全性チェックを実装。
  - ETL パイプラインインタフェースと結果データクラスを追加 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)。
    - ETLResult データクラス: 取得件数、保存件数、品質チェック結果、エラー集約などを保持。to_dict による可視化対応。
    - 差分更新、backfill、品質チェックの設計方針を反映（詳細は doc 想定: DataPlatform.md）。
  - data パッケージの公開用 re-export（ETLResult）を追加。

- Research（因子・特徴量）
  - 研究用ユーティリティ群を追加 (src/kabusys/research/*)。
    - factor_research.py: モメンタム（1/3/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比）、バリュー（PER, ROE）を DuckDB に対する SQL で計算する関数を提供。
    - feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（Spearman）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - それらの便利処理をまとめて __all__ で公開（src/kabusys/research/__init__.py）。
    - 設計方針: DuckDB のみ参照、外部 API へはアクセスせず、ルックアヘッドバイアス回避。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Deprecated
----------
- （初回リリースのため該当なし）

Removed
-------
- （初回リリースのため該当なし）

Security
--------
- OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で解決。未設定時は明示的に ValueError を送出して安全に停止する実装。
- .env 自動読み込みで OS 環境変数を保護する protected 機構を実装（.env.local の上書きなども制御可能）。

Notes / Limitations
-------------------
- OpenAI 関連処理は外部 API 呼び出しを伴うため、実運用では API 利用料やレート制限に注意が必要です。
- DuckDB を前提とした SQL 実装になっており、executemany の空引数に対する互換性考慮など実装上の制約に対応しています。
- news_nlp と regime_detector はテスト容易性のために内部の API 呼び出し関数を patch 可能にしているものの、両モジュールは _call_openai_api を独立実装しておりモジュール間で共有していません（モジュール結合を避けるため）。
- 一部の設計はドキュメント（StrategyModel.md, DataPlatform.md）に基づく想定で実装されています。実運用前に環境変数、データスキーマ（DuckDB テーブル定義）、外部クライアント実装（jquants_client 等）を確認してください。

作者注
-----
この CHANGELOG はリポジトリのソースコードから機能・設計意図を推測して作成したものです。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば日付の確定や詳細な変更差分をコミット履歴に基づいて追記してください。