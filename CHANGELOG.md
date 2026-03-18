Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

注: コードベースから推測した変更点を記載しています（実際のコミット履歴ではありません）。

Changelog
=========

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。  

変更履歴は semver（https://semver.org/lang/ja/）に従います。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基本モジュール群を追加しました。
  - パッケージトップ:
    - src/kabusys/__init__.py: バージョン定義（0.1.0）と公開モジュール一覧。
  - 設定/環境変数管理:
    - src/kabusys/config.py:
      - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
      - 読み込み優先順位: OS 環境 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
      - .env パーサは export KEY=val 形式、クォート囲み、インラインコメント処理、保護された上書きロジック等に対応。
      - Settings クラス：J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの検証付きプロパティを提供。
  - データ取得・保存（Data レイヤ）:
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。主な機能:
        - 固定間隔スロットリングによるレート制限 (120 req/min)。
        - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を考慮。
        - 401 発生時は ID トークンを自動リフレッシュして1回リトライ。
        - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
        - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT で更新）。
        - 型安全な変換ユーティリティ (_to_float/_to_int)、UTC ベースの fetched_at 記録。
    - src/kabusys/data/news_collector.py:
      - RSS ベースのニュース収集モジュールを実装。主な機能:
        - RSS フィード取得（gzip サポート）、最大受信サイズ制限（MAX_RESPONSE_BYTES, デフォルト 10MB）。
        - defusedxml を用いた XML パースで XML Bomb 等に対処。
        - SSRF 対策:
          - URL スキーム制限（http/https のみ）。
          - リダイレクト時のスキーム/ホスト検証用カスタムハンドラ。
          - ホストがプライベート/ループバック等の場合は拒否。
        - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
        - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
        - テキスト前処理（URL 除去、空白正規化）。
        - raw_news へのチャンク挿入（INSERT ... RETURNING を利用）とトランザクション管理、news_symbols への紐付けバルク挿入。
        - 銘柄コード抽出ロジック（4 桁数字の正規表現）と既知コードフィルタリング。
  - スキーマ定義:
    - src/kabusys/data/schema.py:
      - DuckDB 用スキーマ（Raw Layer：raw_prices, raw_financials, raw_news, raw_executions 等）を DDL で定義。
      - カラム制約（NOT NULL、CHECK、PRIMARY KEY）や型を明示。
  - リサーチ / 特徴量探索:
    - src/kabusys/research/factor_research.py:
      - ファクター計算（momentum / volatility / value）を実装。
      - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率（cnt チェックで十分なデータが無ければ None）。
      - calc_volatility: 20 日 ATR（true range 計算）、相対 ATR（atr_pct）、平均売買代金、出来高比率。
      - calc_value: raw_financials と prices_daily を結合して PER/ROE を算出（EPS が 0/欠損時は None）。
      - DuckDB 上でウィンドウ関数を用いた効率的な SQL ベース実装。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定日から各ホライズン（デフォルト: 1,5,21 営業日）先までのリターンを一度に取得。
      - calc_ic: スピアマンの順位相関（ランク相関）による IC 計算（ties は平均ランクで処理、有効レコード < 3 の場合は None）。
      - rank: 同順位（ties）は平均ランクを与える実装（丸めにより ties 検出精度を高める）。
      - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
    - src/kabusys/research/__init__.py: 主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank と zscore_normalize の参照）。
  - パッケージ構成:
    - execution/ と strategy/ の __init__.py を置き、将来的な拡張ポイントを用意（現時点で実装はなし：プレースホルダ）。

Security
- news_collector にて SSRF 対策（スキーム検証、プライベート IP フィルタ、リダイレクト検査）および defusedxml による XML パースを導入。
- J-Quants クライアントは HTTPS 経由でトークンを扱い、失敗時にトークン自動リフレッシュを行うが無限再帰を防ぐ設計（allow_refresh フラグ）。

Performance
- J-Quants API クライアントは固定間隔のスロットリングでレート制限を尊重し、ページネーションをキャッシュ化して効率的に取得。
- calc_forward_returns / factor 計算は DuckDB のウィンドウ関数を活用して一度に複数ホライズンや移動平均を計算、不要な Python 側ループを削減。
- news_collector はチャンク単位でのバルク INSERT を行い、トランザクションをまとめてDBオーバーヘッドを削減。

Internal
- config の .env パーサは export 構文、引用符 handling、インラインコメントの取り扱い（空白前の # をコメントとみなす）など多くの実運用ケースに対応。
- DuckDB への保存関数は PK 欠損行をスキップするログを出すなど堅牢化済み。
- 各所で logger を利用し処理状況・警告を記録するように設計。

Fixed
- 初回リリースにつき該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Notes / Known limitations
- 外部ライブラリへの依存を極力抑える方針（research/feature_exploration は標準ライブラリのみで実装）。ただし実用上は pandas 等を使った方が高速かつ柔軟な集計が可能なケースがあります。
- スキーマファイルは Raw Layer の DDL を含むが、Processed / Feature / Execution レイヤの完全定義は今後追加予定。
- news_collector のホスト名 DNS 解決失敗時は安全側（非プライベート）として扱うため、検証ポリシーは運用に応じて調整推奨。

今後の予定（例）
- execution（発注 / 約定 / ポジション管理）と strategy（戦略実行）モジュールの実装。
- more robust テストカバレッジ（ユニット・統合テスト）、CI での自動検証。
- データ取得/保存の監査ログ強化およびメトリクス収集。

--- 

必要であれば、各ファイルごとの変更点を更に詳細に分解したバージョンや、英語版 CHANGELOG、あるいは release ノートの草案も作成できます。どの形式がよいか教えてください。