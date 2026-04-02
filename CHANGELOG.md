CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

フォーマット:
- Unreleased: 今後の変更
- 各リリース: YYYY-MM-DD 形式で日付を付与

Unreleased
----------
- なし

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 高レベル構成:
    - パッケージエントリポイントを定義 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"

- 環境設定/ローディング機能 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を読み込み
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）
    - OS 環境変数は protected として上書きを防止
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /監視閾値 /実行環境等のプロパティを取得
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装
    - Path 型プロパティ（duckdb/sqlite/pid）や閾値の float キャスト等を備える

- AI ニュース解析・市場レジーム判定 (src/kabusys/ai)
  - ニュースセンチメント解析 (src/kabusys/ai/news_nlp.py)
    - raw_news, news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI (gpt-4o-mini) に JSON モードでバッチ送信
    - バッチサイズ・トークン肥大化対策（最大記事数・最大文字数のトリム）を実装
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ処理
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ、部分成功時の安全な DB 更新（該当コードのみ DELETE → INSERT）
    - ルックアヘッドバイアス防止のため datetime.today() 参照を避け、target_date ベースのウィンドウ計算を採用
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロ経済ニュースの LLM センチメント (重み 30%) を合成して日次で regime_label を算出
    - マクロ記事抽出・LLM 呼び出し（gpt-4o-mini、JSON mode）・リトライ戦略を実装
    - API 失敗時は macro_sentiment = 0.0 のフォールバック（フェイルセーフ）
    - DuckDB を用いた冪等な market_regime テーブル書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の取り扱い
    - ルックアヘッドバイアス防止設計

- Data プラットフォーム機能 (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルと連携した営業日判定・次/前営業日取得・期間内営業日列挙・SQ 判定などを提供
    - DB にデータがない場合は曜日ベースでフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新、バックフィルと健全性チェックを実装
  - ETL パイプライン・インターフェース (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装し、ETL 実行結果の集約（取得/保存件数、品質問題、エラー）を提供
    - pipeline モジュールの方針説明とユーティリティ（差分更新、バックフィル、品質チェック方針）を実装
    - DuckDB を使ったテーブル存在チェック、最大日付取得などの内部ユーティリティを提供
  - jquants_client (参照) 経由での差分取得 → 保存フローを想定した設計

- Research 機能 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、ATR（20 日）、20 日平均売買代金 / 出来高比などを計算する関数を実装
    - DuckDB SQL を用いた高性能集計（ウィンドウ関数等）
    - データ不足時の None 処理とログ出力
  - 特徴量探索・統計 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（任意ホライズン） calc_forward_returns
    - IC（Information Coefficient）計算 calc_ic（スピアマン順位相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ

- 共通実装
  - DuckDB を主要なストレージエンジンとして想定し、SQL+Python での解析を中心に実装
  - ロギングを各モジュールで活用し詳細な INFO/DEBUG/WARNING を出力
  - 重要箇所でのエラーハンドリング（ROLLBACK、API エラー判定、JSON パース失敗のフォールバック）

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし
  - ただし .env パーサで以下を考慮:
    - export KEY=val 形式のサポート
    - クォート内バックスラッシュのエスケープ処理
    - クォートなし値のインラインコメント判定（直前が空白/タブの場合のみ '#' をコメントとみなす）

Security
- 環境変数の取り扱いにおいて OS 環境変数を保護するため .env の上書きを制御する仕組みを実装
- OpenAI API キーが未設定の場合は ValueError を投げて明示的に失敗させる（誤った挙動を避ける）

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を前提としているため、将来の SDK 変更やモデル仕様変更に対して影響を受ける可能性あり（API エラー処理は柔軟に実装済み）
- DuckDB のバージョン差異（リスト型バインドの挙動など）を考慮して一部 executemany による個別 DELETE を採用
- 一部ファイル（pipeline.py の末尾など）に作業中の痕跡や切り取りが見られるため、実装の続き・リファクタリングが必要になる箇所がある可能性あり

作者
- kabusys 開発チーム

---- 

注: 本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のリリースノートやコミット履歴がある場合はそれに合わせて更新してください。