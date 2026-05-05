# TODO: Streamlit での運用フロー拡張

## 背景

Issue #231 で Streamlit 運用ダッシュボード強化（4ビュー構成）は実装済み。

現状の Streamlit は以下の領域を主にカバーしている。

- Home / System Status
- Signal Queue
- Performance
- Strategy Lab

一方で、日々の運用で必要になる以下のフローは、主に CLI ベースで提供されている。

- 初期構築
- テスト運用
- 本番運用
- 障害対応

今後は、CLI を廃止するのではなく、同じ運用ロジックを Streamlit からも利用できるようにして、運用導線を UI 化する。

---

## 方針

### 基本方針

- CLI を捨てて Streamlit に寄せるのではなく、CLI と Streamlit の両方から同じロジックを再利用する
- `collector / report / validation` は Streamlit 非依存のまま維持する
- Streamlit は表示、入力、確認付き実行のフロントエンドとして使う

### Streamlit に向いている範囲

- 可視化
- 確認付き実行
- 限定的な安全操作

### Streamlit に直接持ち込みすぎない範囲

- Task Scheduler の本登録
- OS プロセスの強制停止
- 本番発注に直結する危険操作
- `.env` や秘密情報の恒久保存

---

## 既存資産

### 既存 Streamlit ページ

- `src/kabusys/monitoring/streamlit_dashboard.py`
- `src/kabusys/monitoring/pages/2_Signal_Queue.py`
- `src/kabusys/monitoring/pages/3_Performance.py`
- `src/kabusys/monitoring/pages/4_Strategy_Lab.py`

### 再利用できる既存ロジック

- 初期構築チェック
  - `src/kabusys/validate_config.py`
  - `scripts/setup_db.py`
- 朝の運用前チェック
  - `src/kabusys/operations/pre_market_collector.py`
- 起動直後チェック
  - `src/kabusys/operations/execution_startup_report.py`
- 引け後チェック
  - `src/kabusys/operations/market_close_collector.py`
- テスト運用検証
  - `src/kabusys/tools/paper_verification_report.py`
- 共通データローダー
  - `src/kabusys/monitoring/dashboard_data.py`

---

## 追加したいページ構成

今の 4 ビューを、運用フェーズ基準で以下へ拡張する。

1. `Home`
2. `Initial Setup`
3. `Pre-Market`
4. `Execution Startup`
5. `Intraday Monitor`
6. `Signal Queue`
7. `Performance / Paper Verification`
8. `Failure Recovery`

---

## ページ別 TODO

### 1. Home

- [ ] 既存 Home の責務を再確認する
- [ ] 全体ステータス、Kill Switch、PID、直近エラーの集約ページとして整理する
- [ ] ザラ場監視系の表示が多すぎる場合は `Intraday Monitor` へ分離する

### 2. Initial Setup

- [ ] `validate_config.py` の結果を Streamlit 上で表示する
- [ ] 必須環境変数、設定ファイル、live ガード警告を一覧表示する
- [ ] DuckDB / SQLite / paper DB の存在確認を表示する
- [ ] DB 初期化済みかどうかを表示する
- [ ] Task Scheduler の登録状態を確認表示する
- [ ] 必要なら「既存 CLI を呼ぶだけ」の補助ボタンを追加する

### 3. Pre-Market

- [ ] `pre_market_collector.collect()` を Streamlit から利用する
- [ ] `READY / BLOCKED` 相当の朝判定を画面表示する
- [ ] データ鮮度、Signal Queue、ポジション件数、停止フラグ、Task Scheduler 状態を表示する
- [ ] `run_pre_market_report.py` の出力に依存しないリアルタイム確認ページにする

### 4. Execution Startup

- [ ] Execution 起動直後の確認ビューを追加する
- [ ] `ExecutionStartupReport` の内容をページ表示する
- [ ] `READY / READY_WITH_WARNINGS / BLOCKED` を強調表示する
- [ ] `orders_no_status` と `position_discrepancies` を一覧表示する
- [ ] 再起動前に確認すべき項目への導線をつける

### 5. Intraday Monitor

- [ ] ザラ場監視用の専用ページを分離する
- [ ] monitoring DB の dashboard / risk_logs / trade_logs をまとめて表示する
- [ ] 注文エラー、滞留注文、ドローダウン、Kill Switch 状態を強調表示する
- [ ] Home にあるザラ場中の情報のうち、運用監視寄りのものをここへ寄せる

### 6. Signal Queue

- [ ] 現行ページを維持する
- [ ] 翌営業日の発注予定確認ページとして位置づけを明確にする
- [ ] 必要なら confirmation view 向けの要約指標を追加する

### 7. Performance / Paper Verification

- [ ] 現行 Performance ページを維持する
- [ ] paper_trading 向けの検証タブまたは別ページを追加する
- [ ] `paper_verification_report.py` の集計ロジックを Streamlit 表示へ再利用する
- [ ] 稼働率、送信率、約定率、P95 レイテンシを表示する
- [ ] `paper_trading` と `live` の切替表示ルールを整理する

### 8. Failure Recovery

- [ ] 障害対応専用ページを追加する
- [ ] risk_logs、Kill Switch 状態、PID 状態、注文異常を集約表示する
- [ ] 障害種別ごとに確認ポイントを出し分ける
- [ ] 復旧手順書へのリンクを付ける
- [ ] 危険操作は避け、確認と導線を中心にする

---

## 実装原則

- [ ] `collector / report / validation` を Streamlit から直接再利用する
- [ ] Streamlit ページ内に SQL や業務判定を増やしすぎない
- [ ] 本番系と paper 系で DB・操作制御を分ける
- [ ] 危険操作は `確認 -> dry-run -> 実行` の 3 段階にする
- [ ] 既存 CLI と判定結果がズレないようにロジック重複を避ける

---

## 優先順位

以下の順で実装する。

1. `Pre-Market`
2. `Paper Verification`
3. `Failure Recovery`
4. `Initial Setup`
5. `Execution Startup`
6. `Market Close` 相当の確認ページ追加

---

## 補足

- `Initial Setup` だけは OS / スケジューラ / 環境変数にまたがるため、完全 UI 化ではなく「状態確認 + 既存 CLI / PowerShell の補助実行」に留めるのが安全
- 本番発注や強制停止のような高リスク操作は、原則として Streamlit の中心責務にしない
- まずは「見るだけで価値があるページ」から追加し、操作系は後から限定的に足す
