Changelog
=========
すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニング (MAJOR.MINOR.PATCH) を使用します。

[Unreleased]
------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-21
-------------------

Added
- 初期リリース: kabusys パッケージの公開。
  - パッケージエントリポイント
    - src/kabusys/__init__.py により主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
  - 環境設定管理（src/kabusys/config.py）
    - .env ファイルまたは環境変数からの設定読み込みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .git または pyproject.toml を起点にプロジェクトルートを探索するため、CWD に依存しない動作。
    - .env パーサは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント等を適切に処理。
    - Settings クラスを提供し、必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、KABUSYS_ENV/LOG_LEVEL の検証、デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）を定義。

  - データ取得＆保存（src/kabusys/data/）
    - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
      - 固定間隔レートリミッタ（120 req/min）を実装。
      - リトライ（指数バックオフ、最大 3 回）および 408/429/5xx 対応。
      - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新してリトライ。
      - ページネーション対応。
      - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE による冪等保存。
      - 型変換ユーティリティ（_to_float / _to_int）を提供し、欠損／不正データに対する寛容性を確保。
    - ニュース収集モジュール（src/kabusys/data/news_collector.py）
      - RSS フィード取得・記事整形・正規化・冪等保存の基本ロジックを実装。
      - URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント削除、小文字化など）。
      - defusedxml を用いた安全な XML 解析、受信最大バイト数制限（デフォルト 10MB）を組み込み。
      - SSRF/不正スキーム対策や、挿入チャンク化による DB 負荷軽減を想定した実装。

  - リサーチ機能（src/kabusys/research/）
    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum（1/3/6 ヶ月リターン、MA200 乖離）
      - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
      - Value（PER, ROE）— raw_financials と prices_daily を組み合わせて計算
      - DuckDB のウィンドウ関数を活用した効率的な実装
    - 特徴量探索・統計（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns、複数ホライズン対応、ホライズン検証）
      - IC（スピアマン ρ）計算（calc_ic）、同順位を平均ランクで扱う rank 関数
      - factor_summary による基本統計量（count, mean, std, min, max, median）
    - 依存は標準ライブラリ + duckdb に限定（pandas 等未使用）。

  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で計算した生ファクターを統合・正規化（Z スコア）、±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位の置換を実行）。
    - ユニバースフィルタ実装（株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features テーブルと ai_scores を統合して各銘柄の最終スコア（final_score）を算出。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を実装。カスタム重みは検証・再スケーリングされる。
    - スコア計算のユーティリティ（sigmoid, 平均補完）を実装。欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の平均 regime_score が負の場合）により BUY シグナルを抑制。
    - エグジット判定（SELL）を実装：ストップロス（損益率 <= -8%） / スコア低下（final_score < threshold）。
    - signals テーブルへの日付単位置換（トランザクションで原子性を保証）。
    - 未実装のエグジット条件はコメントで明示（トレーリングストップ / 時間決済は将来対応予定）。

  - strategy パッケージエクスポート（src/kabusys/strategy/__init__.py）
    - build_features, generate_signals を公開。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- defusedxml を使用した RSS/XML の安全解析を採用（XML Bomb 等の脆弱性緩和）。
- ニュースの URL 正規化でトラッキングパラメータを除去し、ID 冪等性を確保する設計。
- .env 読み込みで OS 環境変数を保護する仕組み（自動上書き抑止、override フラグと protected セット）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings のプロパティアクセスで ValueError を投げます。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- テストや CI で .env 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- generate_signals の一部 Exit 条件（トレーリングストップや時間決済）は未実装で、positions テーブル側に peak_price / entry_date 等の追加が必要です。

Known issues / TODO
- ニュース収集モジュールで記事 ID 生成や銘柄紐付け（news_symbols）などの細部処理はドキュメントに設計方針が記載されているが、運用上の微調整（ソース追加・エンティティ抽出・正規表現チューニング等）が必要。
- execution / monitoring パッケージはインタフェースや実装の拡充が必要（現状 execution/__init__.py は空）。
- 一部の SQL/集約ロジックは大規模データでのパフォーマンス検証が必要（DuckDB 上での最適化検討を推奨）。

Authors
- 初期実装者: kabusys 開発チーム（ソース内ドキュメントに設計意図を多く含むため、将来的な拡張や改善がしやすい構成）

License
- ソースにライセンス記載がない場合は、プロジェクト方針に従って LICENSE を別途設定してください。