# CHANGELOG

すべての注目すべき変更はここに記録します。本プロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
バージョンはセマンティックバージョニングに従います。

## [Unreleased]
- 

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買・データ基盤のコア機能を実装・公開しました。主な追加点は以下の通りです。

### Added
- パッケージ全体
  - kabusys パッケージを作成。主要サブパッケージを __all__ で公開（data, research, ai, など）。
  - バージョン情報: 0.1.0

- 設定・環境読み込み (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル／ダブルクォート内エスケープ対応、インラインコメントの扱い等を考慮した堅牢なパーサ。
  - 上書き制御（override）と protected キー（OS 環境変数の保護）をサポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等をプロパティで取得・検証。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（JST ベース → UTC 比較用に変換）を calc_news_window として実装。
    - バッチ処理（最大 20 銘柄／コール）、記事トリム（最大記事数・最大文字数）によるトークン肥大化対策。
    - JSON Mode を利用した堅牢なレスポンスバリデーション（レスポンス復元処理含む）、スコアクリップ、部分書き換え（DELETE → INSERT）による冪等保存。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性: OpenAI 呼び出しは内部関数を patch で差し替え可能。

  - regime_detector.score_regime
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
    - ma200_ratio 計算（target_date 未満のデータのみ使用し、データ不足時は中立扱い）。
    - マクロニュース抽出（マクロキーワードマッチ）、OpenAI 呼び出し（独立実装）による macro_sentiment 評価、リトライ・フォールバック（API 失敗時は 0.0）。
    - 結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK 保護）。
    - ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない、DB クエリは date < target_date 等で排他）。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management
    - market_calendar を扱うマーケットカレンダー管理と夜間更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティ。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 最大探索日数制限や健全性チェック、バックフィル実装等により安定性を確保。

  - pipeline & etl
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー概要などを保持）。
    - 差分更新（最終取得日ベース）、バックフィル、品質チェック（quality モジュール連携）の設計を反映。
    - DuckDB との互換性考慮（executemany の空リスト回避等）や、テスト容易性を考慮した id_token 注入など。

  - etl モジュールから ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム系ファクター。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などのボラティリティ／流動性指標。
    - calc_value: raw_financials から EPS/ROE を用いた PER/ROE 計算（target_date以前の最新財務データを使用）。
    - DuckDB を用いた SQL ベースの実装で、外部発注 API にはアクセスしない設計。

  - feature_exploration
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する汎用実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位の平均ランクを返すユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー。
    - kabusys.data.stats の zscore_normalize を再エクスポート。

### Design / Implementation Notes
- ルックアヘッドバイアス対策: 多くのモジュールで datetime.today()/date.today() の直接参照を避け、target_date ベースの計算を徹底。
- フェイルセーフ設計: 外部 API（OpenAI / J-Quants）失敗時は例外を全体に波及させず、該当処理をフォールバックまたはスキップして継続するよう設計（ただし DB 書き込み失敗等の致命的エラーは伝播）。
- OpenAI 呼び出し: gpt-4o-mini を使用、JSON Mode を利用して厳密な JSON 出力を要求。レスポンスパース失敗時の復元ロジックを実装。
- テスト容易性: OpenAI 呼び出し箇所の内部ラッパー関数（_call_openai_api）を patch で差し替え可能。API キーは引数注入または環境変数で供給可能。
- DuckDB 互換性: executemany に空リストを渡せない旧バージョンへの対処、日付型の安定的取り扱いなどの互換性考慮。
- トランザクション安全: DB 書き込みは明示的に BEGIN/COMMIT/ROLLBACK を使用し、ROLLBACK の失敗もログ出力する堅牢化。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初版のため特記事項なし。環境変数による API キー管理を前提とし、.env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

---

備考:
- 本 CHANGELOG はコードベース（src/ 以下）からの実装意図と仕様を基に作成しています。細かい振る舞いや外部 API の契約は実運用時の設定や API のバージョンに依存します。