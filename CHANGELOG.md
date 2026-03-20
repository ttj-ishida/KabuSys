# Changelog

すべての変更は「Keep a Changelog」のフォーマットに準拠しています。  
このファイルはコードベースの現状（初回リリース v0.1.0）をコード内容から推測して記載したものです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤実装を追加。
  - src/kabusys/__init__.py
    - パッケージ名、バージョン (0.1.0) と公開 API を定義。

- 環境設定・自動 .env ロード機能
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（CWD非依存）。
    - export 形式、クォート文字列、インラインコメント、トラッキングされたクォート内のエスケープに対応するパーサ実装。
    - 読み込み順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定など）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（株価日足、財務データ、市場カレンダーの取得）。
    - レート制限 (120 req/min) を固定間隔スロットリングで遵守する RateLimiter を実装。
    - 冪等性のため DuckDB への保存は ON CONFLICT DO UPDATE を使用。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx 対応）と 401 時のトークン自動リフレッシュを実装。
    - ページネーション対応（pagination_key を用いたループ）を実装。
    - データ変換ユーティリティ (_to_float, _to_int) を実装して入力値の堅牢な変換を行う。
    - fetch_* 系で取得件数のログ出力、save_* 系でスキップ件数と保存件数をログ出力。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを収集し raw_news に保存する処理（記事正規化・ID 生成・冪等保存の方針）を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリのソート）などのユーティリティを実装。
    - セキュリティ配慮: defusedxml の使用、レスポンスサイズ制限（MAX_RESPONSE_BYTES）、SSRF対策方針の記載。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value のファクター計算を実装。
      - モメンタム: mom_1m / mom_3m / mom_6m、MA200 乖離（ウィンドウサイズチェックでデータ不足時は None）。
      - ボラティリティ: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率。
      - バリュー: 最新の raw_financials と当日の価格から PER / ROE を算出。
    - DuckDB SQL を活用した効率的な集計（ウィンドウ関数、部分スキャンレンジ）。
    - 欠損やデータ不足に対する明確な挙動（None での扱い）を実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応し、LEAD を使って一括取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関を実装。サンプル数が不足する場合は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と、count/mean/std/min/max/median を計算する統計サマリー関数を実装。
    - 外部依存を使わず標準ライブラリと DuckDB のみで実装する設計方針。

  - src/kabusys/research/__init__.py
    - 主要な research API を再エクスポート（calc_momentum/calc_volatility/calc_value/zscore_normalize/...）。

- 特徴量エンジニアリング（feature engineering）
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 のクリップを行う。
    - features テーブルへ日付単位での置換（DELETE + バルク INSERT、トランザクションで原子性を担保）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用する方針を明記。

- シグナル生成（signal generation）
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルに保存する実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - スコア変換ユーティリティ: Z スコアをシグモイドで [0,1] に変換、欠損は中立 0.5 で補完。
    - 重みのカスタム化を許可し、入力値検証・再スケール処理を実装（合計が 1 に正規化）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合）による BUY 抑制ロジック。
    - エグジット条件（ストップロス -8%、スコア低下）に基づく SELL シグナル生成。
    - signals テーブルへ日付単位での置換（DELETE + INSERT、トランザクションで原子性を担保）。
    - SELL 優先ポリシー（SELL 対象は BUY リストから除外しランクを再付与）。

- ラッパー / 再エクスポート
  - src/kabusys/strategy/__init__.py
    - build_features と generate_signals を公開 API として再エクスポート。

- データ統計ユーティリティ（外部モジュール参照）
  - zscore_normalize が data.stats に存在する前提で利用（research と strategy で使用）。

### Security
- news_collector は defusedxml を利用して XML の脆弱性（XML Bomb 等）への対策を講じている旨を明記。
- ニュースの URL 正規化や受信サイズ制限により SSRF / メモリ DoS のリスクを低減する方針を導入。

### Notes / Limitations
- execution パッケージは空の初期プレースホルダ（src/kabusys/execution/__init__.py）で、発注処理の実装は含まれていない。
- 一部仕様（例: トレーリングストップ、時間決済）は signal_generator 内で未実装として記載されている（positions テーブルの追加情報が必要）。
- news_collector の具体的な RSS 取得パイプライン（HTTP ヘッダ処理、XML パースの高レベル処理）や raw_news への INSERT 実装はファイルの残り部分に依存するため、本 CHANGELOG では概念・方針を列挙。
- DuckDB のスキーマ（tables: prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）はコードから想定されるが、スキーマ定義自体は別途必要。

---

今後のリリースでは、発注（execution）層の実装、監視/アラート（monitoring）やテストカバレッジ強化、news_collector の完全実装・外部フィード追加などを想定しています。必要であれば CHANGELOG の英語版やリリースノート用の要約を作成します。