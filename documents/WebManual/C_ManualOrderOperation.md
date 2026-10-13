# C. 手動注文メイン運用

- **対象**: kabuステーション API による自動発注を使わず、前日夜・当日朝の候補を見て手動で注文する運用
- **目的**: KabuSys を「自動売買システム」ではなく「売買判断・注文候補・保有評価の支援システム」として使う
- **前提**: 夜間バッチでデータ更新、特徴量生成、シグナル生成、ポートフォリオ構築までは実行する

---

## C-1. 方針

当面の本番運用では、自動発注を主ルートにしない。

kabuステーションの毎日起動、ログイン維持、API 接続確認は運用負荷が高いため、KabuSys は次の役割に集中する。

- 前日夜に翌営業日の BUY / SELL 候補を作る
- 当日朝に注文候補を確認しやすく表示する
- ユーザーが証券画面で手動注文する
- 約定後、手動約定データを KabuSys に投入する
- 投入済みポジションの評価、売却候補、損益確認を行う

Execution Engine は残すが、この運用では起動しない。

---

## C-2. 前日夜の確認

夜間バッチ後に、翌営業日の注文候補を確認する。

```powershell
python scripts/run_night_batch_report.py
python -m kabusys.run_signal_queue_report --save
```

見るもの:

- BUY 候補
- SELL 候補
- 推奨数量
- 想定約定金額
- `READY` / `READY_WITH_WARNINGS` / `BLOCKED`

判断:

- `READY`: 翌朝の手動注文候補として採用可能
- `READY_WITH_WARNINGS`: 警告内容を確認して採用可否を判断
- `BLOCKED`: 翌朝の注文は原則見送り

---

## C-3. 当日朝の確認

当日朝は、実際に注文するかを最終判断する。

```powershell
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
```

見るもの:

- データ鮮度
- 停止フラグ
- 今日の候補
- 注文数量
- 前日終値ベースの想定金額

この運用では `scripts/start_system.py --component execution` は実行しない。

---

## C-4. 手動注文

ユーザーが証券画面で注文する。

基本方針:

- BUY は候補一覧から選ぶ
- SELL は売却候補と保有状況を見て判断する
- 発注数量は KabuSys の推奨数量を上限目安にする
- 見送り理由がある銘柄は無理に注文しない

注文後は、約定結果を必ず控える。

控える項目:

| 項目 | 内容 |
| ---- | ---- |
| 銘柄コード | 例: `72030` |
| 売買 | `buy` / `sell` |
| 数量 | 約定株数 |
| 約定単価 | 平均約定単価 |
| 約定日 | `YYYY-MM-DD` |
| メモ | 任意 |

---

## 手動保有の SELL 判定と買い増し

`.env` で次を設定すると、手動約定の保有が自動売買と同じロジックで評価される。

    MANUAL_TRADING_ENABLED=true
    MANUAL_TRADING_INITIAL_CASH=3000000

- 既定値: `MANUAL_TRADING_ENABLED` は既定 `false`（未設定なら手動保有は判定に含めない）。`MANUAL_TRADING_INITIAL_CASH` は未設定時 `PORTFOLIO_VALUE` を使う。

- 夜間バッチ（strategy_signal）が手動保有に損切り・トレーリングストップ・保有期限・スコア低下などの SELL 判定を行い、該当銘柄を `manual_action_queue` に「売却候補」として記録する。KabuSys は発注しない。
- 夜 LINE の SELL 行に株数・理由・`[手動保有]` が表示される。
- 手動保有中の銘柄が BUY 候補になった場合、目標株数との差分だけが提示され、`[買い増し]` と表示される。
- BUY 株数は「元手 − 手動買付額 + 売却額 + 保有時価」を総資産として計算する。
- Streamlit **Manual Trades → 売却候補** タブで、候補を「対応済み」「見送り」に更新できる。「日付で絞り込む」にチェックを入れると、指定日の候補だけに絞り込める。売却したら必ず「入力」タブで SELL 約定を登録する。

---

## C-5. 約定データ投入

約定後は、CSV ではなく CLI で 1 件ずつ登録する。

確認だけ行い、DB に保存しない場合:

```powershell
python -m kabusys.manual_trades add --date 2026-09-17 --code 72030 --side buy --qty 100 --price 3016 --note W1_08候補
```

DB に保存する場合:

```powershell
python -m kabusys.manual_trades add --date 2026-09-17 --code 72030 --side buy --qty 100 --price 3016 --note W1_08候補 --apply
```

対話式で入力する場合:

```powershell
python -m kabusys.manual_trades wizard
```

登録内容を確認する場合:

```powershell
python -m kabusys.manual_trades list --date 2026-09-17
```

手動保有ポジションを確認する場合:

```powershell
python -m kabusys.manual_trades positions --date 2026-09-17
```

`--date` 以前で最新の終値を使い、取得原価、評価額、含み損益、実現損益、合計損益を表示する。休日を指定した場合は、直前取引日の終値が自動的に使われる。

GUI で入力・損益確認する場合は、Streamlit の **Manual Trades** ページを使う。**手動ポジション** タブの評価日は前日が初期値で、任意の日付へ変更できる。GUI も CLI と同じ `manual_trades` テーブルを使う。

---

## C-6. 引け後の確認

```powershell
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --save
```

見るもの:

- 注文した銘柄の終値
- 保有銘柄の含み損益
- 翌営業日の SELL 候補
- 翌営業日の BUY 候補

---

## C-7. 自動発注へ戻さない条件

次の条件が解消するまでは、自動発注へ戻さない。

- kabuステーションを毎朝安定して起動できない
- API 接続確認が運用負荷になっている
- 手動注文で十分に運用判断できている
- Paper Trading の4週間検証が完了していない

---

## C-8. 実装TODO

- 手動ポジション評価レポートの SELL 助言接続
- 日次評価レポートへの手動ポジション統合
- 手動ポジション向け SELL 候補レポート
- 前日夜・当日朝の注文候補レポート強化
- 自動発注を使わない運用モードの明示

関連TODO: [TODO_ManualTradeImportAdvisoryMode.md](../08_Operations/TODO_ManualTradeImportAdvisoryMode.md)
