Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記載します。
このプロジェクトは Keep a Changelog の方針に従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
改善予定・既知の未実装/拡張点（コード内コメントから推測）:

- 戦略 / エグジット条件の拡張
  - トレーリングストップ（直近最高値から -10%）の実装予定（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）の実装予定。
- news_collector
  - INSERT RETURNING による「実際に挿入されたレコード数」の正確な取得（現状はバルク挿入）。
- API クライアントの改善
  - リトライポリシーやレート制御の更なるテスト・チューニング。
- テスト・運用面
  - 自動化テストの整備（特に DB 周り・ネットワークエラー時の挙動）。
  - ドキュメント補強（StrategyModel.md / DataPlatform.md 等の参照整備）。
- その他
  - 監視（monitoring）・実行（execution）モジュールの具現化（パッケージは存在するが実装は限定的／未提供箇所あり）。

0.1.0 - 2026-03-19
-----------------
最初の公開リリース（コードベースから推測した初期実装内容）。

Added
- 基本パッケージ構成
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - バージョン番号を 0.1.0 に設定。

- 設定管理
  - 環境変数・設定管理モジュールを追加 (kabusys.config.Settings)。
    - .env / .env.local ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val 形式やクォート、コメントの扱いに対応した .env パーサ実装。
    - 必須値チェック用の _require()、環境 (development/paper_trading/live) やログレベルの検証ロジックを提供。
    - デフォルトの DB パス（duckdb/sqlite）、Slack / Kabu API / J-Quants の設定プロパティを提供。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを追加 (kabusys.data.jquants_client)。
    - レート制限 (120 req/min) に基づく固定間隔スロットリング実装（_RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）、特定ステータスコード (408/429/5xx) のリトライ処理。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応（pagination_key 連携）。
    - データの DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 保存時に fetched_at を UTC で記録し、冪等性のため ON CONFLICT ... DO UPDATE を利用。
    - 型安全な数値変換ユーティリティ（_to_float / _to_int）。

- ニュース収集
  - news_collector モジュールを追加 (kabusys.data.news_collector)。
    - RSS フィードの取得・パース（defusedxml を利用した安全な XML パース）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF 対策やトラッキングパラメータの取り扱い方針が明示。
    - 記事ID生成ルール（正規化後の SHA-256 ハッシュ先頭などで冪等性を担保する設計方針）。

- 研究（research）モジュール
  - factor_research モジュール（kabusys.research.factor_research）を追加。
    - モメンタム（calc_momentum）：1M/3M/6M リターン、MA200 乖離率を計算。
    - ボラティリティ（calc_volatility）：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：最新の財務データと株価から PER/ROE を計算。
    - DuckDB での窓関数を活用した実装。データ不足時には None を返す保護あり。
  - feature_exploration モジュール（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト 1/5/21）での将来リターンを計算。
    - IC（calc_ic）：ファクターと将来リターンの Spearman ランク相関（ties を平均ランクで扱う）を実装。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - ランキングユーティリティ（rank）：同順位は平均ランクを割り当てる実装。
  - research パッケージ __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング（feature_engineering）
  - build_features を実装 (kabusys.strategy.feature_engineering)。
    - research の calc_momentum / calc_volatility / calc_value を利用して原始ファクターを取得。
    - ユニバースフィルタ（最低株価、最低平均売買代金）を適用。
    - 数値ファクターを zscore_normalize（外部ユーティリティ）で正規化し ±3 にクリップ。
    - features テーブルへ日付単位での置換（DELETE→INSERT でトランザクションにより原子性を保証）。
    - 欠損や非有限値の扱いを明記。

- シグナル生成（signal_generator）
  - generate_signals を実装 (kabusys.strategy.signal_generator)。
    - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - 個別スコアはシグモイド変換や反転（ボラティリティ）などで [0,1] にマッピング。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付け和で計算（デフォルト重みを持ち、ユーザ指定 weights を検証して正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら BUY を抑制、サンプル数閾値あり）。
    - BUY（閾値 0.60）・SELL（ストップロス -8% / スコア低下）を生成。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへの日付単位置換をトランザクションで実施。
    - ログ出力・警告を適切に行う実装。

Changed
- 初回リリースのため、各モジュールは設計方針・制約・未実装の注意点をドキュメント（docstring/comments）で明示。

Fixed
- （該当なし）初回リリースとして新規追加が中心。

Security
- news_collector で defusedxml を採用し XML 関連の攻撃（XML Bomb 等）を軽減する設計。
- RSS URL 正規化や受信バイト上限、SSRF を意識した取扱いがコメントで明記されている。

Notes / その他
- DuckDB を中心としたデータ処理設計。各関数は DuckDB 接続を引数に取り、prices_daily / raw_financials / features / ai_scores / positions 等のテーブルを操作・参照する想定。
- 多くの箇所で「ルックアヘッドバイアスを防ぐ」設計判断が明示されており、target_date 以前のデータのみを参照する方針が徹底されている。
- execution / monitoring モジュールはパッケージ名として存在するが、今回のスナップショットでは発注 API 連携・監視ロジックの具現化は限定的。

作者注記（推測）
- コード内コメントが丁寧に書かれており、設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づいて段階的に実装されていることが推測されます。
- 今後はポジション管理（peak_price, entry_date 等）用のテーブル拡張、news と銘柄紐付けの実装、より詳しい監視・実行層の実装が見込まれます。

--- 

（必要であれば、各リリースエントリをさらに細かく分割したり、日付やコミットハッシュを追加できます。現状はコードの内容から推測可能な主要変更をまとめた初期 CHANGELOG です。）