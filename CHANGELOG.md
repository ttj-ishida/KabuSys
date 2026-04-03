CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

注: 以下のリリース内容は、提供されたコードベースから推測・要約したものです。

Unreleased
----------
- 今後の変更・修正をここに記載します。

[0.1.0] - 2026-04-03
--------------------
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。
主な追加点、設計方針、既知の制約を以下に列挙します。

Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定し、data / strategy / execution / monitoring を公開モジュールとして定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD に依存しない設計）。
    - 読み込み順序は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - export KEY=val 形式やシングル/ダブルクォート、インラインコメント、エスケープを考慮したパーサを実装。
    - .env 読込時の上書き挙動（override / protected）を提供し、OS 環境変数保護に対応。
  - Settings クラスで各種設定値をプロパティで提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログ等）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - duckdb_path, sqlite_path, pid_file_path などは Path として返す。

- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング (news_nlp)
    - raw_news / news_symbols から銘柄別のニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
    - 1チャンクあたり最大 20 銘柄、1銘柄あたり最大記事数・最大文字数でトリムする仕組み。
    - レート制限 (429)・ネットワーク断・タイムアウト・5xx に対して指数バックオフでのリトライ実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results キー、コード整合性、数値検査）、スコアは ±1 にクリップ。
    - API 呼び出し部分は _call_openai_api で抽象化しており、テスト時に差し替え可能。
    - ai_scores テーブルへの冪等的な書き込み（対象コードのみ DELETE → INSERT）を実装。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime に保存。
    - マクロセンチメントは news_nlp の窓集計ユーティリティ calc_news_window と raw_news 絞り込みの結果を OpenAI に渡して評価（gpt-4o-mini、JSON Mode）。
    - API 呼び出しの再試行ロジック、API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - DuckDB を用いた計算・DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - テスト容易性のため OpenAI 呼び出しをモジュール間で共有せず独立実装。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定 / SQ 判定 / 前後の営業日取得 / 期間内営業日列挙のユーティリティを実装。
    - 市場カレンダー未取得時は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - JPX カレンダーを J-Quants API から差分取得して market_calendar を更新するバッチジョブ calendar_update_job を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー等を集約）。
    - 差分更新、バックフィル、品質チェックを想定した設計（J-Quants クライアントと quality モジュールとの連携を前提）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ等の下地を実装。
  - etl モジュールの公開インターフェースとして ETLResult を再エクスポート。

- Research / Factor 分析 (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum 実装。データ不足時の None 処理あり。
    - Volatility / Liquidity: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率を計算する calc_volatility 実装。NULL による true_range 処理に注意。
    - Value: raw_financials から最新財務データを取得して PER（eps が無効な場合は None）と ROE を計算する calc_value 実装。
    - DuckDB SQL を主体に自己完結的に計算する設計（DB の prices_daily / raw_financials のみ参照）。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）のリターンを一度の SQL で取得する実装。
    - IC 計算（calc_ic）：スピアマン相関（ランク）を手続き的に計算する実装（ties は平均ランク）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を標準ライブラリのみで算出。
    - ランク変換ユーティリティ（rank）を提供。
  - research パッケージの __all__ にて主要関数を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの扱い
  - news_nlp / regime_detector の両関数は api_key 引数または環境変数 OPENAI_API_KEY を期待。未設定時は ValueError を送出して明示的に失敗する（キー漏洩抑止のため環境変数参照）。

Notes / Implementation details / 既知の制約
- DuckDB 前提
  - 多くの処理は DuckDB 接続を前提としており、テーブル存在やバージョン差分（executemany の空リスト扱い等）に注意している。DuckDB のバージョン差異により挙動が変わる可能性がある。
- OpenAI JSON Mode を前提
  - LLM の応答は JSON のみを期待する設計だが、現実には前後に余計なテキストが混ざる場合があるため復元ロジックを実装している。
- フェイルセーフ設計
  - 外部 API（OpenAI, J-Quants等）が失敗してもシステム全体を停止させない設計（部分スキップ・ゼロフォールバック等）を採用。重要な失敗はログに記録して上位に伝播させる箇所もある（DB 書き込み失敗時は例外伝播）。
- テストフック
  - OpenAI 呼び出しは _call_openai_api 関数で抽象化されており、ユニットテストで差し替え可能（unittest.mock.patch 推奨）。
- ルックアヘッドバイアス対策
  - 全ての時間ウィンドウ計算やデータ参照は target_date を明示的に受け取り、date.today()/datetime.today() を不要にする方針（バックテストや研究でのルックアヘッドを回避）。
- ログ・監視設定
  - 環境変数で CPU/MEM/DISK 閾値や PID/KILL フラグのパスが設定可能。ログレベルは LOG_LEVEL により検証あり（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）。

今後の予定（例）
- execution / monitoring の実装拡張（実際の発注ロジック、安全装置、プロセス監視）
- データ品質チェックモジュール(quality) の詳細実装と ETL への統合強化
- テストカバレッジの追加（特に OpenAI 回りの応答バリデーションと DuckDB 書き込み部分）

著記
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のプロジェクト運用状況やリリースノートとは差異がある可能性があります。