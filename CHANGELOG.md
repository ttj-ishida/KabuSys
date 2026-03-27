# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このパッケージの初回公開リリースです。

## [0.1.0] - 2026-03-27

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, research, ai, execution, strategy, monitoring（__all__ に準拠）
  - バージョン: 0.1.0

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定
    - 読み込み順序: OS 環境変数 > .env > .env.local（.env.local は上書き）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS 環境変数は protected として上書きされない
  - .env 行パーサー実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートあり/なしで異なる挙動）
  - Settings クラスを提供（環境変数の検証・既定値を含むプロパティ）
    - J-Quants、kabuステーション、Slack、データベースパス、環境（development/paper_trading/live）、ログレベル等
    - 必須環境変数未設定時は ValueError を送出

- AI (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュースを集約
    - OpenAI (gpt-4o-mini) へ最大 20 銘柄ずつバッチ送信し JSON Mode でセンチメントを取得
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - トークン肥大化対策: 1銘柄あたり最大記事数・文字数を制限
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装
    - レスポンスのバリデーションとスコアの ±1.0 クリップ
    - DuckDB への冪等的書き込み（該当コードのみ DELETE → INSERT）
    - テスト用に内部の OpenAI 呼び出しをモック可能
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - LLM は gpt-4o-mini、出力は厳密な JSON を期待
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）
    - マクロ記事が無い場合は LLM を呼ばず macro_sentiment=0.0 とする
    - API エラー時はフェイルセーフで macro_sentiment=0.0 にフォールバック
    - 冪等な DB 書き込み (BEGIN / DELETE / INSERT / COMMIT) を実施
    - テスト用に OpenAI 呼び出しの差し替えを想定した設計

- 研究（Research）機能 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）
    - ボラティリティ / 流動性: 20日 ATR、ATR/価格、20日平均売買代金、出来高比率
    - バリュー: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から取得）
    - DuckDB を用いた SQL + Python 実装（prices_daily / raw_financials のみ参照）
    - 結果は (date, code) をキーとする辞書リストで返却
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターンの計算（複数ホライズン: デフォルト [1,5,21]）
    - IC（Information Coefficient）: スピアマンのランク相関を計算
    - ランク変換ユーティリティ（同順位は平均ランク）
    - ファクター統計サマリー（count, mean, std, min, max, median）
    - 標準ライブラリのみで実装（pandas 等に依存しない）

- データプラットフォーム（Data） (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar がない場合は曜日ベースでフォールバック（週末を非営業日扱い）
    - DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫した挙動を保証
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult データクラスを追加（取得件数、保存件数、品質チェック結果、エラーリスト 等を格納）
    - テーブル最終日付の判定ユーティリティ、差分取得とバックフィル方針を実装
    - 品質チェックモジュールとの連携設計（品質問題は収集して上位で判断）
    - jquants_client 経由での保存処理を想定（save_* 関数との協調）

- テスト・運用上の配慮
  - datetime.today()/date.today() を主要なアルゴリズムで参照しない設計（ルックアヘッドバイアス防止）
  - OpenAI 呼び出しを差し替えられるよう関数分離（ユニットテスト容易化）
  - DuckDB の executemany の制約（空リスト不可）に配慮した書き込み実装

### 変更
- （初回リリースのためなし）

### 修正
- （初回リリースのためなし）

### 削除
- （初回リリースのためなし）

### 破壊的変更
- なし（初回リリース）

### 既知の制約・注意点
- OpenAI API のキーは引数で注入可能（api_key）だが、未指定時は環境変数 OPENAI_API_KEY に依存する。未設定時は ValueError が発生する仕様。
- DuckDB の日付型や executemany のバインド互換性に注意（実装で回避策をとっています）。
- .env パーシングは POSIX ライクな記法を想定しているが、極端な入力は未検証。必要に応じて .env.example を参照してください。

---

今後の予定（例）
- モニタリング・実行モジュールの充実（発注ロジック、監視アラート）
- ETL の品質チェック強化と自動リトライ戦略の追加
- ベンチマーク用の Research ユーティリティ拡張

（この CHANGELOG はコードベースから推測して作成しています。文言や仕様は実装の進展に合わせて更新してください。）