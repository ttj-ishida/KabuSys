CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------
- なし（初回リリース以降の変更はここに記載）

[0.1.0] - 2026-03-19
--------------------
初回公開リリース。主要機能の実装と基盤ライブラリを提供します。

Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - 公開 API: kabusys.strategy.build_features / kabusys.strategy.generate_signals をエクスポート。

- 環境設定
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得可能に（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - .env パーサーを強化（コメント・export プレフィックス・クォート内エスケープ処理・インラインコメントの扱い等）。
  - 設定値の検証（KABUSYS_ENV の制約、LOG_LEVEL の許容値チェック、必須値チェック）を追加。
  - 環境自動読み込みを一時的に無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- Data 層
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。主な特徴:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ処理。
    - ページネーション対応のデータ取得 (日足 / 財務 / カレンダー)。
    - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar へ ON CONFLICT 更新）。
    - 型変換ユーティリティ（_to_float / _to_int）と取得時刻（fetched_at の UTC 記録）。
    - モジュール内トークンキャッシュによるページネーション間でのトークン共有。

  - ニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。主な特徴:
    - RSS フィード取得・記事整形・URL 正規化（トラッキングパラメータ除去）機能。
    - 記事IDは正規化後のハッシュを生成して冪等性を担保。
    - defusedxml を利用した XML セキュリティ対策、受信バイト数制限、SSRF 対策の考慮。
    - DB へのバルク挿入のチャンク化とトランザクション最適化。

- Research（リサーチ）層
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）:
    - モメンタム (1M/3M/6M)、200日移動平均乖離率 (ma200_dev)。
    - ボラティリティ/流動性（20日 ATR、atr_pct、avg_turnover、volume_ratio）。
    - バリュー（PER、ROE）を raw_financials と prices_daily の組合せで算出。
    - DuckDB の SQL とウィンドウ関数を活用した実装（営業日欠損・ウィンドウ不足時の None ハンドリング）。
  - 特徴量探索モジュールを実装（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（horizons デフォルト [1,5,21]、複数ホライズン同時取得）。
    - IC（Spearman の ρ）計算（ランク化・同順位は平均ランク）。
    - factor_summary による統計サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリに依存しない実装（標準ライブラリのみ）。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。

- Strategy（戦略）層
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）:
    - research から生ファクターを取得し、ユニバースフィルタ（最低株価・20日平均売買代金）適用。
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（BEGIN/DELETE/INSERT/COMMIT による原子性確保）。
  - シグナル生成モジュール（src/kabusys/strategy/signal_generator.py）:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントから final_score を算出。
    - デフォルト重み・閾値を定義し、ユーザ渡しの weights を検証・再スケール。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル閾値を満たす場合）。
    - BUY（閾値超）/SELL（ストップロス / スコア低下）シグナルの生成ロジック実装。
    - positions / prices_daily を参照したエグジット判定、SELL 優先ポリシー（BUY から除外）。
    - signals テーブルへの日付単位置換を実施（トランザクションで原子性確保）。

Changed
- 設計・実装方針の明文化
  - 各モジュールにルックアヘッドバイアス抑制、外部 API や本番口座への直接アクセスを避ける方針を明記。
  - DuckDB を中心としたローカル分析基盤を前提とした設計を採用。

Fixed
- 安全性・堅牢性向上（実装時に考慮）
  - .env 読み込み時のファイル読み取り失敗を警告で捕捉しプロセスを継続。
  - ネットワーク・HTTP エラー時の細かなリトライ制御（Retry-After の尊重、429 特殊扱い）。
  - DuckDB への保存時に PK 欠損の行をスキップして警告ログを出すように調整。

Security
- 外部入力の扱いに関する配慮
  - news_collector で defusedxml を利用して XML 関連の脆弱性を緩和。
  - URL 正規化でトラッキングパラメータ除去・スキームチェックを行い SSRF 対策を考慮。

Notes / Known limitations
- いくつかの戦略条件は未実装（feature_engineering / signal_generator 内に注釈あり）:
  - トレーリングストップや時間決済など、positions テーブルに追加情報（peak_price / entry_date 等）が必要な条件は未実装。
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理ではパフォーマンス上のチューニング余地あり。
- news_collector の完全な RSS パーサー、記事と銘柄の紐付け処理（news_symbols との連携）は今後の拡張を予定。

Authors
- 実装チーム（コード内ドキュメントを参照）。

License
- リポジトリの LICENSE を参照してください。