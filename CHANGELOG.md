CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

現在のバージョンは 0.1.0 です。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-20
--------------------

初期公開リリース。本バージョンでは日本株の自動売買システムのコア機能群を実装しました。
主要な追加点、設計上の注意点、既知の制限などを以下にまとめます。

Added
-----

- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として公開。
  - 公開モジュール: data, strategy, execution, monitoring（execution パッケージは空の __init__ を含む）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（デフォルト）。
  - 自動ロードの検索はパッケージファイルの位置からプロジェクトルート(.git または pyproject.toml)を探索するため、CWDに依存しない。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパース機能強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応（クォート内はインラインコメント無視）
    - クォート無し時の # を先行スペースでコメントとして扱う
  - 必須環境変数取得用の Settings API を提供（例: settings.jquants_refresh_token）。
  - サポートされる環境値の検証（KABUSYS_ENV, LOG_LEVEL）。

- データ取得 & 保存 (kabusys.data)
  - J-Quants API クライアント (jquants_client.py)
    - 日足・財務・マーケットカレンダーの取得関数を提供（ページネーション対応）。
    - API レート制限を守る固定間隔スロットリング（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）と HTTP ステータスに基づく再試行。
    - 401 受信時にリフレッシュトークンを用いた自動トークン再取得を試行し1回リトライ。
    - データを DuckDB に冪等的に保存するユーティリティ（ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ（_to_float/_to_int）で入力の堅牢性を確保。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得・正規化・raw_news への冪等保存機能を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
    - トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリソートなどの正規化実装。
    - defusedxml を使用して XML 攻撃を防止。
    - SSRF / 非 HTTP スキーム拒否、受信サイズ上限(MAX_RESPONSE_BYTES) によるメモリ DoS 対策。
    - DB 挿入はバルク＆チャンク化して効率化。

- 研究 (research)
  - ファクター計算 (factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily の組合せで算出
    - DuckDB SQL を活用した高速な集計処理（窓関数利用）
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（默认 [1,5,21]）を同時取得
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（同順位は平均ランク）
    - factor_summary: 基本統計（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理、丸め誤差対策として round(..., 12) を使用
  - research パッケージは外部ライブラリ（pandas等）に依存せずに設計。

- 戦略 (strategy)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research で計算した raw ファクターをマージ・ユニバースフィルタ（株価>=300円、20日平均売買代金>=5億円）適用・Zスコア正規化（zscore_normalize の利用）して features テーブルへアップサート。
    - Z スコアは ±3 でクリップして外れ値影響を抑制。
    - 処理は日付単位で置換（トランザクション＋バルク挿入で原子性確保）。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成。
    - コンポーネント: momentum/value/volatility/liquidity/news（デフォルト重みあり）。
    - スコア変換にシグモイド関数を使用。欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム（ai_scores の regime_score 平均が負）を検出すると BUY シグナルを抑制。
    - SELL 条件（実装済み）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性）。
    - 重み指定はバリデーション・再スケールされ、無効値はスキップ。

- DB スキーマ依存（期待するテーブル）
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, signals, positions, raw_news などに対する読み書きを行う想定。

Changed
-------

- （新規リリースのため該当なし）

Fixed
-----

- （新規リリースのため該当なし）

Security
--------

- J-Quants クライアントでのトークン自動リフレッシュと限定的な再試行設計により認証失敗時の暴走を防止。
- news_collector で defusedxml を使用して XML ベースの攻撃を低減。
- RSS URL 正規化とトラッキングパラメータ除去により同一記事の重複登録と追跡パラメータ混入を防止。
- HTTP レスポンスサイズ制限によりメモリ DoS を抑止。
- .env の自動読み込みで OS 環境変数を上書きしない（保護キー保護機構）。

Deprecated
----------

- なし

Removed
-------

- なし

Known issues / Limitations
--------------------------

- シグナル生成の一部エグジット条件は未実装：
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
  これらは comments に TODO として明記されており、将来の拡張予定。
- Value ファクターの一部（PBR・配当利回り）は未実装。
- positions テーブルのメタ情報（peak_price / entry_date 等）が現在ない場合、トレーリング処理等が動作しない。
- news_collector の RSS パースは一般的なケースを想定。極端に壊れた/奇妙なフィードに対する継続的な堅牢性テストが必要。
- DuckDB のスキーマ（列名・型）に依存しているため、既存 DB スキーマと不整合があると動作しない。初期導入時はスキーマ定義ファイル（別途提供予定）に従ってください。

Migration / Usage notes
-----------------------

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- オプション / デフォルト:
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live) default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) default: INFO
- .env の自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

Contributing
------------

- バグ報告・機能提案は Issue にて受け付けてください。
- 大幅な設計変更（特にデータベーススキーマやシグナルロジックの仕様変更）は後方互換性を損なう可能性があるため、事前に設計議論をお願いします。

Acknowledgements
----------------

- 本プロジェクトは DuckDB をデータ処理に積極的に利用し、外部依存を最小化する方針で実装されています。